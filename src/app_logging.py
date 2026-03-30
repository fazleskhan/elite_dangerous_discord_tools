"""Project-specific logging setup and runtime configuration support.

[README:LOGGING]
* Logging uses Loguru via `src/app_logging.py`.
* Runtime configuration is externalized in `config/loguru.json`.
* Config changes are hot-reloaded via watchdog file events.
* Default behavior writes datestamped file logs under `logs/`,
  archives/compresses old logs under `logs/archive`, and expires archived
  logs by retention rules.
* Console output is colorized and split by level (`info/warn` on stdout,
  `error` on stderr by default).
[/README]
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any

try:
    from autologging import traced
except ImportError:

    def traced(target: Any) -> Any:
        return target


from dotenv import load_dotenv
from loguru import logger as _logger
from loguru_config_loader import load_config_file, merge_nested_dicts
from loguru_runtime import apply_runtime_config, make_min_level_filter
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from defaults import (
    DEFAULT_APPLICATION_LOG_PATH,
    DEFAULT_LOGURU_CONFIG,
    DEFAULT_LOGURU_CONFIG_PATH,
    DEFAULT_LOG_ARCHIVE_DIR,
    DEFAULT_LOG_COLOR_FORMAT,
    DEFAULT_LOG_TEXT_FORMAT,
)

_WATCHER: _LoguruConfigWatcher | None = None
_WATCHER_LOCK = threading.Lock()


@traced
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Any = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    return merge_nested_dicts(base, override)


def load_loguru_config(config_path: Path) -> dict[str, Any]:
    return load_config_file(config_path, DEFAULT_LOGURU_CONFIG)


def _level_number(level_name: str) -> int:
    return int(_logger.level(level_name.upper()).no)


def _normalize_path(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve()


def _archive_stale_logs(
    log_path: Path,
    archive_dir: Path,
    archive_after_days: int,
    now: float | None = None,
) -> None:
    cutoff_seconds = archive_after_days * 24 * 60 * 60
    current_time = time.time() if now is None else now
    archive_dir.mkdir(parents=True, exist_ok=True)
    for candidate in log_path.parent.glob(f"{log_path.stem}*{log_path.suffix}"):
        if candidate == log_path or not candidate.is_file():
            continue
        if candidate.parent == archive_dir:
            continue
        if current_time - candidate.stat().st_mtime < cutoff_seconds:
            continue
        archive_path = archive_dir / f"{candidate.name}.gz"
        with candidate.open("rb") as source, gzip.open(archive_path, "wb") as target:
            shutil.copyfileobj(source, target)
        candidate.unlink()


def _delete_expired_archives(
    archive_dir: Path,
    archive_retention_days: int,
    now: float | None = None,
) -> None:
    if not archive_dir.exists():
        return
    cutoff_seconds = archive_retention_days * 24 * 60 * 60
    current_time = time.time() if now is None else now
    for archive_file in archive_dir.glob("*.gz"):
        if not archive_file.is_file():
            continue
        if current_time - archive_file.stat().st_mtime > cutoff_seconds:
            archive_file.unlink()


def _stdout_filter(min_level_name: str):
    return make_min_level_filter(
        _level_number(min_level_name),
        max_level_number=_level_number("ERROR"),
    )


def _stderr_filter(min_level_name: str):
    return make_min_level_filter(_level_number(min_level_name))


def _file_filter(min_level_name: str):
    return make_min_level_filter(_level_number(min_level_name))


def apply_loguru_config(config: dict[str, Any]) -> None:
    apply_runtime_config(
        config,
        logger=_logger,
        stdout=sys.stdout,
        stderr=sys.stderr,
        default_application_log_path=DEFAULT_APPLICATION_LOG_PATH,
        default_log_archive_dir=DEFAULT_LOG_ARCHIVE_DIR,
        default_log_color_format=DEFAULT_LOG_COLOR_FORMAT,
        default_log_text_format=DEFAULT_LOG_TEXT_FORMAT,
        level_number=_level_number,
        normalize_path=_normalize_path,
        archive_stale_logs=_archive_stale_logs,
        delete_expired_archives=_delete_expired_archives,
    )


def configure_standard_logging_intercept() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)


def configure_logging(
    config_path: str | Path = DEFAULT_LOGURU_CONFIG_PATH,
) -> None:
    load_dotenv()
    resolved_path = Path(config_path)
    global _WATCHER
    with _WATCHER_LOCK:
        if _WATCHER is None:
            watcher = _LoguruConfigWatcher(resolved_path)
            _WATCHER = watcher
            watcher.start()


@traced
class _LoguruConfigWatcher:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self._config_mtime_ns: int | None = None
        self._apply_lock = threading.Lock()
        self._observer: BaseObserver | None = None

    def start(self) -> None:
        self._apply_if_needed(force=True)
        config = self._load_config()
        watch_enabled = bool(config.get("watch", {}).get("enabled", True))
        if not watch_enabled:
            return
        if self._observer is None:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            event_handler = _ConfigFileEventHandler(self)
            observer = Observer()
            observer.schedule(
                event_handler, str(self.config_path.parent), recursive=False
            )
            observer.start()
            self._observer = observer
            _logger.debug("Started watchdog observer for {}", self.config_path)

    def handle_fs_event(self, event: FileSystemEvent) -> None:
        if self._event_targets_config(event):
            self._apply_if_needed(force=False)

    def _event_targets_config(self, event: FileSystemEvent) -> bool:
        src_path = Path(os.fsdecode(event.src_path)).resolve()
        if src_path == self.config_path:
            return True
        dest_path = getattr(event, "dest_path", None)
        if dest_path is None:
            return False
        return Path(os.fsdecode(dest_path)).resolve() == self.config_path

    def _apply_if_needed(self, force: bool) -> None:
        try:
            current_mtime_ns = self.config_path.stat().st_mtime_ns
        except FileNotFoundError:
            current_mtime_ns = None

        if not force and current_mtime_ns == self._config_mtime_ns:
            return

        config = self._load_config()
        with self._apply_lock:
            self._configure_logger(config)
            self._config_mtime_ns = current_mtime_ns
            _logger.debug("Reloaded Loguru configuration from {}", self.config_path)

    def _load_config(self) -> dict[str, Any]:
        return load_loguru_config(self.config_path)

    @staticmethod
    def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        return _merge_dict(base, override)

    def _configure_logger(self, config: dict[str, Any]) -> None:
        apply_loguru_config(config)
        configure_standard_logging_intercept()


@traced
class _ConfigFileEventHandler(FileSystemEventHandler):
    def __init__(self, watcher: _LoguruConfigWatcher):
        self._watcher = watcher

    def on_modified(self, event: FileSystemEvent) -> None:
        self._watcher.handle_fs_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._watcher.handle_fs_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._watcher.handle_fs_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._watcher.handle_fs_event(event)
