from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def make_min_level_filter(
    min_level_number: int,
    *,
    max_level_number: int | None = None,
) -> Callable[[dict[str, Any]], bool]:
    """Build a Loguru filter that constrains records by level number.

    The returned callable accepts Loguru record dictionaries and keeps only
    messages at or above the configured minimum level, optionally stopping
    before a supplied upper bound.
    """

    def _filter(record: dict[str, Any]) -> bool:
        level_no = int(record["level"].no)
        if max_level_number is None:
            return level_no >= min_level_number
        return min_level_number <= level_no < max_level_number

    return _filter


def apply_runtime_config(
    config: dict[str, Any],
    *,
    logger: Any,
    stdout: Any,
    stderr: Any,
    default_application_log_path: Path,
    default_log_archive_dir: Path,
    default_log_color_format: str,
    default_log_text_format: str,
    level_number: Callable[[str], int],
    normalize_path: Callable[[str | Path], Path],
    archive_stale_logs: Callable[[Path, Path, int], None],
    delete_expired_archives: Callable[[Path, int], None],
) -> None:
    """Apply the active runtime logging configuration to Loguru.

    The function clears existing sinks, configures stdout and stderr outputs
    from the provided settings, and optionally prepares file logging including
    archive rotation and archive-retention cleanup.
    """
    logger.remove()

    stdout_config = config.get("stdout", {})
    if bool(stdout_config.get("enabled", True)):
        logger.add(
            stdout,
            level=str(stdout_config.get("level", "INFO")),
            colorize=bool(stdout_config.get("colorize", True)),
            format=str(stdout_config.get("format", default_log_color_format)),
            filter=make_min_level_filter(
                level_number(str(stdout_config.get("level", "INFO"))),
                max_level_number=level_number("ERROR"),
            ),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

    stderr_config = config.get("stderr", {})
    if bool(stderr_config.get("enabled", True)):
        logger.add(
            stderr,
            level=str(stderr_config.get("level", "ERROR")),
            colorize=bool(stderr_config.get("colorize", True)),
            format=str(stderr_config.get("format", default_log_color_format)),
            filter=make_min_level_filter(
                level_number(str(stderr_config.get("level", "ERROR")))
            ),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

    file_config = config.get("file", {})
    if bool(file_config.get("enabled", True)):
        log_path = normalize_path(
            str(file_config.get("path", default_application_log_path))
        )
        archive_dir = normalize_path(
            str(file_config.get("archive_dir", default_log_archive_dir))
        )
        archive_after_days = int(file_config.get("archive_after_days", 7))
        archive_retention_days = int(file_config.get("archive_retention_days", 30))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        archive_stale_logs(log_path, archive_dir, archive_after_days)
        delete_expired_archives(archive_dir, archive_retention_days)
        logger.add(
            str(log_path),
            level=str(file_config.get("level", "INFO")),
            rotation=str(file_config.get("rotation", "00:00")),
            format=str(file_config.get("format", default_log_text_format)),
            filter=make_min_level_filter(
                level_number(str(file_config.get("level", "INFO")))
            ),
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )
