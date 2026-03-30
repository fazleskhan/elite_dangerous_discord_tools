from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any


def merge_nested_dicts(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Deep-merge two configuration dictionaries.

    The helper copies the base configuration and then recursively merges nested
    dictionaries from the override so runtime logging settings can inherit
    defaults while replacing only the keys they explicitly specify.
    """
    merged: dict[str, Any] = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config_file(
    config_path: Path,
    default_config: dict[str, Any],
) -> dict[str, Any]:
    """Load Loguru configuration from disk with project defaults as fallback.

    The loader returns a merged configuration when a file exists and is valid,
    tries the optional `loguru_config` helper package first, and falls back to
    plain JSON loading when that package is unavailable or unusable.
    """
    config = dict(default_config)
    if not config_path.exists():
        return config

    with suppress(Exception):
        import loguru_config

        loader = getattr(loguru_config, "LoguruConfig", None)
        if loader is not None and hasattr(loader, "load"):
            loaded = loader.load(str(config_path))
            if isinstance(loaded, dict):
                return merge_nested_dicts(default_config, loaded)

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return config
    if isinstance(raw, dict):
        return merge_nested_dicts(default_config, raw)
    return config
