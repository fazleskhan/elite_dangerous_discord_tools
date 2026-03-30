"""Project-specific logging setup and runtime configuration support.

[README:LOGGING]
* Logging uses Loguru via `src/ed_app_logging.py`.
* Runtime configuration is externalized in `config/loguru.json`.
* Config changes are hot-reloaded via watchdog file events.
* Default behavior writes datestamped file logs under `logs/`,
  archives/compresses old logs under `logs/archive`, and expires archived
  logs by retention rules.
* Console output is colorized and split by level (`info/warning` on stdout,
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
from ed_loguru_config_loader import load_config_file, merge_nested_dicts
from ed_loguru_runtime import apply_runtime_config, make_min_level_filter
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from ed_defaults import (
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
    """Forward standard-library logging records into Loguru.

    Third-party libraries often log through the stdlib logging module. This
    handler translates those records into Loguru calls so the project can keep
    one consistent logging pipeline and formatting setup.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Convert one standard-library logging record into a Loguru log call.

        The method resolves the appropriate Loguru level, adjusts call depth so
        source locations remain useful, and forwards the original message and
        exception information into Loguru.
        """
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
    """Deep-merge two logging configuration dictionaries.

    The function preserves the base shape and recursively overlays override
    values so configuration fragments can replace only the keys they specify.
    """
    return merge_nested_dicts(base, override)


def load_loguru_config(config_path: Path) -> dict[str, Any]:
    """Load the active Loguru configuration from disk.

    The helper delegates to the shared config loader so logging setup always
    starts from the project's default configuration and overlays any file-based
    overrides.
    """
    return load_config_file(config_path, DEFAULT_LOGURU_CONFIG)


def _level_number(level_name: str) -> int:
    """Return the numeric Loguru value for a level name.

    The logging runtime uses numeric levels when building min/max filters, so
    this helper centralizes the conversion from symbolic names.
    """
    return int(_logger.level(level_name.upper()).no)


def _normalize_path(path_value: str | Path) -> Path:
    """Resolve a user-supplied logging path into an absolute filesystem path.

    Logging configuration may provide relative or home-directory paths, so this
    helper expands and resolves them before file sinks and archive logic use
    them.
    """
    return Path(path_value).expanduser().resolve()


def _archive_stale_logs(
    log_path: Path,
    archive_dir: Path,
    archive_after_days: int,
    now: float | None = None,
) -> None:
    """Compress and move stale log files into the archive directory.

    The helper scans sibling log files, skips the active log and already
    archived files, and gzips any file older than the configured archive
    threshold into the archive directory.
    """
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
    """Delete archived log files older than the retention window.

    The helper walks the archive directory and removes any compressed log whose
    modification time has aged beyond the configured retention cutoff.
    """
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
    """Build the stdout log filter for non-error records.

    Console output is split across stdout and stderr, so stdout accepts records
    from the configured minimum level up to but excluding error-level messages.
    """
    return make_min_level_filter(
        _level_number(min_level_name),
        max_level_number=_level_number("ERROR"),
    )


def _stderr_filter(min_level_name: str):
    """Build the stderr log filter for error-level records and above.

    The filter uses the configured minimum level and allows all higher-severity
    messages so stderr carries the error stream.
    """
    return make_min_level_filter(_level_number(min_level_name))


def _file_filter(min_level_name: str):
    """Build the file-sink log filter.

    File logging keeps records at or above the configured minimum level, which
    lets the runtime share one consistent filtering helper across sink types.
    """
    return make_min_level_filter(_level_number(min_level_name))


def apply_loguru_config(config: dict[str, Any]) -> None:
    """Apply the resolved logging configuration to the process-wide Loguru logger.

    The function delegates sink creation and archive housekeeping to the shared
    runtime helper while supplying this module's path, level, and cleanup
    helpers.
    """
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
    """Redirect stdlib logging through the Loguru intercept handler.

    This keeps library logs and application logs on the same Loguru-based path
    so formatting and sink routing stay consistent.
    """
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)


def configure_logging(
    config_path: str | Path = DEFAULT_LOGURU_CONFIG_PATH,
) -> None:
    """Configure process-wide logging exactly once and start config watching.

    The function loads environment variables, creates the singleton config
    watcher on first use, and relies on that watcher to apply the initial
    configuration and any later file-based reloads.
    """
    load_dotenv()
    resolved_path = Path(config_path)
    global _WATCHER
    with _WATCHER_LOCK:
        if _WATCHER is None:
            # Logging is configured once per process; subsequent callers only
            # ensure env vars were loaded and reuse the existing watcher.
            watcher = _LoguruConfigWatcher(resolved_path)
            _WATCHER = watcher
            watcher.start()


@traced
class _LoguruConfigWatcher:
    """Watch the Loguru config file and reapply logging when it changes.

    The watcher tracks the last-seen config modification time, serializes
    reconfiguration work behind a lock, and optionally starts a watchdog
    observer so file edits trigger runtime logging reloads.
    """

    def __init__(self, config_path: Path):
        """Store config-file tracking state for future reload checks.

        The watcher keeps the resolved config path, the last applied mtime, and
        the synchronization primitives needed to safely reload logging.
        """
        self.config_path = config_path.resolve()
        self._config_mtime_ns: int | None = None
        self._apply_lock = threading.Lock()
        self._observer: BaseObserver | None = None

    def start(self) -> None:
        """Apply the initial config and start filesystem watching if enabled.

        Startup forces one configuration pass, reads the resolved config to
        discover whether file watching is enabled, and then attaches a watchdog
        observer to the config directory when needed.
        """
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
        """React to a filesystem event that may affect the config file.

        The method filters unrelated events and only attempts a reload when the
        event references the watched config path.
        """
        if self._event_targets_config(event):
            self._apply_if_needed(force=False)

    def _event_targets_config(self, event: FileSystemEvent) -> bool:
        """Return whether a filesystem event targets the watched config file.

        Watchdog events may report either a source path or a destination path
        depending on the file operation, so the helper checks both forms.
        """
        # Watchdog may report either the source or destination path depending on
        # the filesystem event type, so we treat either side as a config hit.
        src_path = Path(os.fsdecode(event.src_path)).resolve()
        if src_path == self.config_path:
            return True
        dest_path = getattr(event, "dest_path", None)
        if dest_path is None:
            return False
        return Path(os.fsdecode(dest_path)).resolve() == self.config_path

    def _apply_if_needed(self, force: bool) -> None:
        """Reload logging when the config file has changed or reload is forced.

        The method compares the current config mtime with the last applied
        value, loads the current config, and performs the actual reconfiguration
        under a lock to prevent overlapping reloads.
        """
        try:
            current_mtime_ns = self.config_path.stat().st_mtime_ns
        except FileNotFoundError:
            current_mtime_ns = None

        if not force and current_mtime_ns == self._config_mtime_ns:
            return

        config = self._load_config()
        with self._apply_lock:
            # Re-checking under the lock prevents overlapping watchdog events
            # from interleaving Loguru reconfiguration work.
            self._configure_logger(config)
            self._config_mtime_ns = current_mtime_ns
            _logger.debug("Reloaded Loguru configuration from {}", self.config_path)

    def _load_config(self) -> dict[str, Any]:
        """Load the current config-file contents with project defaults applied.

        The watcher delegates the actual parsing and merge behavior to the
        module-level config loader helper.
        """
        return load_loguru_config(self.config_path)

    @staticmethod
    def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep-merge two config dictionaries for watcher tests and helpers.

        This static wrapper preserves the watcher's historical helper surface
        while delegating the actual merge behavior to the module-level helper.
        """
        return _merge_dict(base, override)

    def _configure_logger(self, config: dict[str, Any]) -> None:
        """Apply a loaded config to Loguru and stdlib logging interception.

        Reloading logging requires both the Loguru sink setup and stdlib
        interception to be refreshed, so the watcher performs both steps here.
        """
        apply_loguru_config(config)
        configure_standard_logging_intercept()


@traced
class _ConfigFileEventHandler(FileSystemEventHandler):
    """Watchdog event adapter that forwards file events to the config watcher.

    The handler keeps the watchdog-specific callback names small and delegates
    the actual reload decision to `_LoguruConfigWatcher`.
    """

    def __init__(self, watcher: _LoguruConfigWatcher):
        """Store the watcher that will handle relevant filesystem events.

        The event handler itself is intentionally thin and exists mainly to
        adapt watchdog's callback interface to the watcher API.
        """
        self._watcher = watcher

    def on_modified(self, event: FileSystemEvent) -> None:
        """Forward config-file modifications to the watcher.

        Watchdog invokes this callback when a file changes, and the handler
        simply passes the event along for config-path filtering and reload logic.
        """
        self._watcher.handle_fs_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Forward config-file creation events to the watcher.

        Creating or recreating the config file can change runtime logging, so
        the handler delegates the event to the watcher.
        """
        self._watcher.handle_fs_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Forward config-file deletion events to the watcher.

        Deleting the config file may require logging to fall back to defaults,
        so the watcher needs to inspect the event.
        """
        self._watcher.handle_fs_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Forward config-file move events to the watcher.

        Moves may replace or remove the active config file, so the watcher must
        inspect the event's source and destination paths.
        """
        self._watcher.handle_fs_event(event)
