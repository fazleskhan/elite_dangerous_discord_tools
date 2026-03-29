from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger as _logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

DEFAULT_CONFIG_PATH = Path("config/loguru.json")
DEFAULT_LOG_PATH = Path("logs/application.log")
DEFAULT_TEXT_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | tid={thread.id} | "
    "{name}:{function}:{line} | {message}"
)
DEFAULT_COLOR_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | <cyan>tid={thread.id}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

_WATCHER: "_LoguruConfigWatcher | None" = None
_WATCHER_LOCK = threading.Lock()

_DEFAULT_CONFIG: dict[str, Any] = {
    "stdout": {
        "enabled": True,
        "level": "INFO",
        "colorize": True,
        "format": DEFAULT_COLOR_FORMAT,
    },
    "stderr": {
        "enabled": True,
        "level": "ERROR",
        "colorize": True,
        "format": DEFAULT_COLOR_FORMAT,
    },
    "file": {
        "enabled": True,
        "path": str(DEFAULT_LOG_PATH),
        "level": "INFO",
        "rotation": "00:00",
        "compression": "gz",
        "retention": "30 days",
        "format": DEFAULT_TEXT_FORMAT,
    },
    "watch": {
        "enabled": True,
    },
}


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
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_loguru_config(config_path: Path) -> dict[str, Any]:
    config = dict(_DEFAULT_CONFIG)
    if not config_path.exists():
        return config

    try:
        import loguru_config

        loader = getattr(loguru_config, "LoguruConfig", None)
        if loader is not None and hasattr(loader, "load"):
            loaded = loader.load(str(config_path))
            if isinstance(loaded, dict):
                return _merge_dict(_DEFAULT_CONFIG, loaded)
    except Exception:
        pass

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return config
    if isinstance(raw, dict):
        return _merge_dict(_DEFAULT_CONFIG, raw)
    return config


def _level_number(level_name: str) -> int:
    return int(_logger.level(level_name.upper()).no)


def _normalize_path(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve()


def _stdout_filter(min_level_name: str):
    min_level_number = _level_number(min_level_name)

    def _filter(record: dict[str, Any]) -> bool:
        level_no = int(record["level"].no)
        return min_level_number <= level_no < _level_number("ERROR")

    return _filter


def _stderr_filter(min_level_name: str):
    min_level_number = _level_number(min_level_name)

    def _filter(record: dict[str, Any]) -> bool:
        return int(record["level"].no) >= min_level_number

    return _filter


def _file_filter(min_level_name: str):
    min_level_number = _level_number(min_level_name)

    def _filter(record: dict[str, Any]) -> bool:
        return int(record["level"].no) >= min_level_number

    return _filter


def apply_loguru_config(config: dict[str, Any]) -> None:
    _logger.remove()

    stdout_config = config.get("stdout", {})
    if bool(stdout_config.get("enabled", True)):
        _logger.add(
            sys.stdout,
            level=str(stdout_config.get("level", "INFO")),
            colorize=bool(stdout_config.get("colorize", True)),
            format=str(stdout_config.get("format", DEFAULT_COLOR_FORMAT)),
            filter=_stdout_filter(str(stdout_config.get("level", "INFO"))),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

    stderr_config = config.get("stderr", {})
    if bool(stderr_config.get("enabled", True)):
        _logger.add(
            sys.stderr,
            level=str(stderr_config.get("level", "ERROR")),
            colorize=bool(stderr_config.get("colorize", True)),
            format=str(stderr_config.get("format", DEFAULT_COLOR_FORMAT)),
            filter=_stderr_filter(str(stderr_config.get("level", "ERROR"))),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

    file_config = config.get("file", {})
    if bool(file_config.get("enabled", True)):
        log_path = _normalize_path(str(file_config.get("path", DEFAULT_LOG_PATH)))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            str(log_path),
            level=str(file_config.get("level", "INFO")),
            rotation=str(file_config.get("rotation", "00:00")),
            compression=file_config.get("compression", "gz"),
            retention=file_config.get("retention", "30 days"),
            format=str(file_config.get("format", DEFAULT_TEXT_FORMAT)),
            filter=_file_filter(str(file_config.get("level", "INFO"))),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )


def configure_standard_logging_intercept() -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)


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
        load_dotenv()
        resolved_path = Path(config_path)
        global _WATCHER
        with _WATCHER_LOCK:
            if _WATCHER is None:
                _WATCHER = _LoguruConfigWatcher(resolved_path)
                _WATCHER.start()

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.trace(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.info(message, *args, **kwargs)

    def warn(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.warning(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.warn(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        _logger.exception(message, *args, **kwargs)

    def opt(self, *args: Any, **kwargs: Any) -> Any:
        return _logger.opt(*args, **kwargs)
