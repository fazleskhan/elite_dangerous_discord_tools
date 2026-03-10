from __future__ import annotations

import gzip
import json
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger as _logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

DEFAULT_CONFIG_PATH = Path("config/loguru.json")
_WATCHER: "_LoguruConfigWatcher | None" = None
_WATCHER_LOCK = threading.Lock()

_DEFAULT_CONFIG: dict[str, Any] = {
    "console": {
        "enabled": True,
        "level": "INFO",
        "colorize": True,
        "format": (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>tid={thread.id}</cyan> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    },
    "file": {
        "enabled": True,
        "path": "logs/application.log",
        "level": "INFO",
        "rotation": "00:00",
        "retention_days": 14,
        "archive_directory": "logs/archive",
        "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | tid={thread.id} | {name}:{function}:{line} | {message}",
    },
    "watch": {
        "enabled": True,
    },
}


class _LoguruConfigWatcher:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self._config_mtime_ns: int | None = None
        self._apply_lock = threading.Lock()
        self._observer: Observer | None = None

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
        src_path = Path(event.src_path).resolve()
        if src_path == self.config_path:
            return True
        dest_path = getattr(event, "dest_path", None)
        if dest_path is None:
            return False
        return Path(dest_path).resolve() == self.config_path

    def _apply_if_needed(self, force: bool) -> None:
        try:
            current_mtime_ns = self.config_path.stat().st_mtime_ns
        except FileNotFoundError:
            current_mtime_ns = None

        # Skip reloads when the file timestamp did not change.
        if not force and current_mtime_ns == self._config_mtime_ns:
            return

        config = self._load_config()
        with self._apply_lock:
            self._configure_logger(config)
            self._config_mtime_ns = current_mtime_ns
            _logger.debug("Reloaded Loguru configuration from {}", self.config_path)

    def _load_config(self) -> dict[str, Any]:
        config = dict(_DEFAULT_CONFIG)
        if self.config_path.exists():
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    config = self._merge_dict(_DEFAULT_CONFIG, raw)
            except json.JSONDecodeError:
                # Keep defaults when the config file is temporarily invalid.
                pass

        return config

    def _configure_logger(self, config: dict[str, Any]) -> None:
        _logger.remove()

        console_config = config.get("console", {})
        if bool(console_config.get("enabled", True)):
            _logger.add(
                sys.stderr,
                level=str(console_config.get("level", "INFO")),
                colorize=bool(console_config.get("colorize", True)),
                format=str(
                    console_config.get("format", _DEFAULT_CONFIG["console"]["format"])
                ),
                backtrace=False,
                diagnose=False,
                enqueue=True,
            )

        file_config = config.get("file", {})
        if bool(file_config.get("enabled", True)):
            log_path = Path(str(file_config.get("path", "logs/application.log")))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            archive_dir = Path(
                str(file_config.get("archive_directory", "logs/archive"))
            )
            archive_dir.mkdir(parents=True, exist_ok=True)

            retention_days = int(file_config.get("retention_days", 14))
            _logger.add(
                str(log_path),
                level=str(file_config.get("level", "INFO")),
                rotation=str(file_config.get("rotation", "00:00")),
                retention=self._retention_cleanup(archive_dir, retention_days),
                compression=self._compress_to_archive_factory(archive_dir),
                format=str(
                    file_config.get("format", _DEFAULT_CONFIG["file"]["format"])
                ),
                backtrace=False,
                diagnose=False,
                enqueue=True,
            )

    @staticmethod
    def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        # Recursively merge nested sections so partial config overrides work.
        merged: dict[str, Any] = dict(base)
        for key, value in override.items():
            if (
                isinstance(value, dict)
                and key in merged
                and isinstance(merged[key], dict)
            ):
                merged[key] = _LoguruConfigWatcher._merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _compress_to_archive_factory(archive_dir: Path):
        archive_dir.mkdir(parents=True, exist_ok=True)

        def _compress(source_path: str) -> None:
            # Loguru passes the rotated file path; we gzip it into archive_dir.
            source = Path(source_path)
            archive_target = archive_dir / f"{source.name}.gz"
            with source.open("rb") as source_stream:
                with gzip.open(archive_target, "wb") as archive_stream:
                    shutil.copyfileobj(source_stream, archive_stream)
            source.unlink(missing_ok=True)

        return _compress

    @staticmethod
    def _retention_cleanup(archive_dir: Path, retention_days: int):
        seconds_limit = max(retention_days, 1) * 24 * 60 * 60
        archive_dir.mkdir(parents=True, exist_ok=True)

        def _cleanup(paths: list[str]) -> None:
            # Loguru sends current log file candidates; we also prune archived .gz files.
            now = time.time()
            for path_str in paths:
                path = Path(path_str)
                try:
                    if now - path.stat().st_mtime > seconds_limit:
                        path.unlink(missing_ok=True)
                except FileNotFoundError:
                    continue
            for archived_file in archive_dir.glob("*.gz"):
                try:
                    if now - archived_file.stat().st_mtime > seconds_limit:
                        archived_file.unlink(missing_ok=True)
                except FileNotFoundError:
                    continue

        return _cleanup


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


class EDLoggingUtils:
    """OO logging utility facade for IoC composition."""

    _instance: "EDLoggingUtils | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)

    @staticmethod
    def create(config_path: str | Path = DEFAULT_CONFIG_PATH) -> "EDLoggingUtils":
        with EDLoggingUtils._instance_lock:
            if EDLoggingUtils._instance is None:
                logging_utils = EDLoggingUtils(config_path)
                EDLoggingUtils._initialize_watcher(logging_utils.config_path)
                EDLoggingUtils._instance = logging_utils
        return EDLoggingUtils._instance

    @staticmethod
    def _initialize_watcher(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        """Configure Loguru and start a background watcher for hot-reload."""
        load_dotenv()
        resolved_path = Path(config_path)
        global _WATCHER
        with _WATCHER_LOCK:
            if _WATCHER is None:
                _WATCHER = _LoguruConfigWatcher(resolved_path)
                _WATCHER.start()

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.exception(message, *args, **kwargs)

    def opt(self, *args: Any, **kwargs: Any) -> Any:
        return _logger.opt(*args, **kwargs)
