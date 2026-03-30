from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_INIT_DIR: Path = Path("./init")
DEFAULT_EXPORT_DIR: Path = Path("./data/export")
DEFAULT_TINYDB_NAME: Path = Path("./data/ed_route.db")
DEFAULT_DISCORD_LOG_NAME: str = "discord_bot.log"
DEFAULT_REDIS_STORE_NAME: str = "eddt"
DEFAULT_LOGURU_CONFIG_PATH: Path = Path("config/loguru.json")
DEFAULT_APPLICATION_LOG_PATH: Path = Path("logs/application.log")
DEFAULT_LOG_ARCHIVE_DIR: Path = Path("logs/archive")
DEFAULT_LOG_TEXT_FORMAT: str = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | tid={thread.id} | "
    "{name}:{function}:{line} | {message}"
)
DEFAULT_LOG_COLOR_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | <cyan>tid={thread.id}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
DEFAULT_LOGURU_CONFIG: dict[str, Any] = {
    "stdout": {
        "enabled": True,
        "level": "INFO",
        "colorize": True,
        "format": DEFAULT_LOG_COLOR_FORMAT,
    },
    "stderr": {
        "enabled": True,
        "level": "ERROR",
        "colorize": True,
        "format": DEFAULT_LOG_COLOR_FORMAT,
    },
    "file": {
        "enabled": True,
        "path": str(DEFAULT_APPLICATION_LOG_PATH),
        "level": "INFO",
        "rotation": "00:00",
        "archive_dir": str(DEFAULT_LOG_ARCHIVE_DIR),
        "archive_after_days": 7,
        "archive_retention_days": 30,
        "format": DEFAULT_LOG_TEXT_FORMAT,
    },
    "watch": {
        "enabled": True,
    },
}
