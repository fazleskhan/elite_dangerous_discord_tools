import logging
import os
from dotenv import load_dotenv


def resolve_log_level(default: int = logging.INFO) -> int:
    """Resolve log level from LOG_LEVEL env var (name like DEBUG or numeric)."""
    load_dotenv()
    raw_level = os.getenv("LOG_LEVEL")
    if raw_level is None:
        return default

    normalized = raw_level.strip()
    if not normalized:
        return default

    if normalized.isdigit():
        return int(normalized)

    named_level = getattr(logging, normalized.upper(), None)
    if isinstance(named_level, int):
        return named_level

    return default
