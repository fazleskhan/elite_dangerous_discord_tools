import json
import os
import time
from pathlib import Path

from watchdog.events import FileModifiedEvent

import logging_utils as logging_utils


def test_merge_dict_recursively_merges_nested_values():
    # User config should be able to override only selected nested keys.
    base = {
        "console": {"enabled": True, "level": "INFO"},
        "file": {"enabled": True},
    }
    override = {
        "console": {"level": "DEBUG"},
        "new_key": {"value": 1},
    }

    merged = logging_utils._merge_dict(base, override)

    assert merged == {
        "console": {"enabled": True, "level": "DEBUG"},
        "file": {"enabled": True},
        "new_key": {"value": 1},
    }


def test_setup_logging_initializes_watcher_once(monkeypatch, tmp_path):
    created_paths = []
    start_calls = 0

    class FakeWatcher:
        # Captures constructor/start usage without creating real watchdog threads.
        def __init__(self, config_path: Path):
            created_paths.append(Path(config_path))

        def start(self):
            nonlocal start_calls
            start_calls += 1

    monkeypatch.setattr(logging_utils, "_WATCHER", None)
    monkeypatch.setattr(logging_utils, "_LoguruConfigWatcher", FakeWatcher)
    monkeypatch.setattr(logging_utils, "load_dotenv", lambda: None)

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    logging_utils.setup_logging(first_path)
    logging_utils.setup_logging(second_path)

    assert created_paths == [first_path]
    assert start_calls == 1


def test_hot_reload_reapplies_config_when_file_changes(monkeypatch, tmp_path):
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    config_path = tmp_path / "loguru.json"
    config_path.write_text(
        json.dumps(
            {
                "console": {"level": "INFO"},
                "file": {"level": "INFO"},
                "watch": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    watcher = logging_utils._LoguruConfigWatcher(config_path)
    applied_levels = []

    def record_config(config):
        # Track each applied level tuple to verify a reload happened.
        applied_levels.append((config["console"]["level"], config["file"]["level"]))

    monkeypatch.setattr(watcher, "_configure_logger", record_config)

    watcher._apply_if_needed(force=True)

    initial_mtime = config_path.stat().st_mtime_ns
    config_path.write_text(
        json.dumps(
            {
                "console": {"level": "DEBUG"},
                "file": {"level": "DEBUG"},
                "watch": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    # Ensure filesystem mtime changes so the watcher can detect an update.
    for _ in range(10):
        if config_path.stat().st_mtime_ns != initial_mtime:
            break
        time.sleep(0.01)

    if config_path.stat().st_mtime_ns == initial_mtime:
        forced_ns = initial_mtime + 1_000_000
        os.utime(config_path, ns=(forced_ns, forced_ns))

    watcher.handle_fs_event(FileModifiedEvent(str(config_path)))

    assert applied_levels == [("INFO", "INFO"), ("DEBUG", "DEBUG")]
