import gzip
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

import ed_app_logging
import ed_defaults


def main() -> None: ...


class FakeSinkLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.add_calls: list[dict[str, Any]] = []
        self.remove_calls = 0
        self.opt_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            self.calls.append((name, args, kwargs))

    def remove(self) -> None:
        with self._lock:
            self.remove_calls += 1

    def add(self, sink: Any, **kwargs: Any) -> int:
        with self._lock:
            self.add_calls.append({"sink": sink} | kwargs)
            return len(self.add_calls)

    def level(self, name: str):
        levels = {"TRACE": 5, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
        return type("Level", (), {"name": name, "no": levels[name]})()

    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("trace", message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("debug", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("info", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("warning", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("error", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._record("exception", message, *args, **kwargs)

    def opt(self, *args: Any, **kwargs: Any) -> str:
        with self._lock:
            self.opt_calls.append((args, kwargs))
        return "opt-result"

    def calls_for(self, name: str) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
        with self._lock:
            return [
                (args, kwargs)
                for call_name, args, kwargs in self.calls
                if call_name == name
            ]


class FakeObserver:
    def __init__(self) -> None:
        self.schedule_calls: list[tuple[Any, str, bool]] = []
        self.started = False

    def schedule(self, handler: Any, path: str, recursive: bool = False) -> None:
        self.schedule_calls.append((handler, path, recursive))

    def start(self) -> None:
        self.started = True


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ed_app_logging, "_WATCHER", None)


@pytest.fixture()
def fake_logger(monkeypatch: pytest.MonkeyPatch) -> FakeSinkLogger:
    logger = FakeSinkLogger()
    monkeypatch.setattr(ed_app_logging, "_logger", logger)
    monkeypatch.setattr(ed_app_logging, "_logger", logger)
    return logger


def test_merge_dict_recursively_merges_nested_values() -> None:
    base = {
        "console": {"enabled": True, "level": "INFO"},
        "file": {"enabled": True, "path": "logs/app.log"},
    }
    override = {
        "console": {"level": "DEBUG"},
        "watch": {"enabled": False},
    }

    merged = ed_app_logging._LoguruConfigWatcher._merge_dict(base, override)

    assert merged == {
        "console": {"enabled": True, "level": "DEBUG"},
        "file": {"enabled": True, "path": "logs/app.log"},
        "watch": {"enabled": False},
    }


def test_load_config_returns_defaults_and_ignores_invalid_json(tmp_path: Path) -> None:
    loaded_defaults = ed_app_logging._LoguruConfigWatcher(
        tmp_path / "missing.json"
    )._load_config()
    assert loaded_defaults["stdout"]["level"] == "INFO"
    assert loaded_defaults["file"]["path"] == str(
        ed_defaults.DEFAULT_APPLICATION_LOG_PATH
    )

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{ invalid", encoding="utf-8")
    assert (
        ed_app_logging._LoguruConfigWatcher(invalid_path)._load_config()["file"]["path"]
        == "logs/application.log"
    )


def test_load_config_merges_user_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    config_path.write_text(
        json.dumps(
            {
                "stdout": {"level": "DEBUG"},
                "file": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    loaded = ed_app_logging._LoguruConfigWatcher(config_path)._load_config()

    assert loaded["stdout"]["level"] == "DEBUG"
    assert loaded["stdout"]["enabled"] is True
    assert loaded["file"]["enabled"] is False
    assert loaded["watch"]["enabled"] is True


def test_archive_stale_logs_moves_old_rotated_logs_to_archive(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_path = log_dir / "application.log"
    log_path.write_text("current", encoding="utf-8")
    rotated_log = log_dir / "application.2026-03-01.log"
    rotated_log.write_text("rotated", encoding="utf-8")
    archive_dir = log_dir / "archive"
    now = 30 * 24 * 60 * 60
    old_time = now - (8 * 24 * 60 * 60)

    ed_app_logging.os.utime(rotated_log, (old_time, old_time))

    ed_app_logging._archive_stale_logs(log_path, archive_dir, 7, now=now)

    archived_log = archive_dir / f"{rotated_log.name}.gz"
    assert not rotated_log.exists()
    assert archived_log.exists()
    with gzip.open(archived_log, "rt", encoding="utf-8") as handle:
        assert handle.read() == "rotated"


def test_delete_expired_archives_removes_old_archives(tmp_path: Path) -> None:
    archive_dir = tmp_path / "logs" / "archive"
    archive_dir.mkdir(parents=True)
    stale_archive = archive_dir / "application.2026-01-01.log.gz"
    stale_archive.write_text("stale", encoding="utf-8")
    fresh_archive = archive_dir / "application.2026-03-01.log.gz"
    fresh_archive.write_text("fresh", encoding="utf-8")
    now = 40 * 24 * 60 * 60
    stale_time = now - (31 * 24 * 60 * 60)
    fresh_time = now - (5 * 24 * 60 * 60)

    ed_app_logging.os.utime(stale_archive, (stale_time, stale_time))
    ed_app_logging.os.utime(fresh_archive, (fresh_time, fresh_time))

    ed_app_logging._delete_expired_archives(archive_dir, 30, now=now)

    assert not stale_archive.exists()
    assert fresh_archive.exists()


def test_configure_logger_adds_console_and_file_sinks(
    tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "config.json")
    log_path = tmp_path / "logs" / "app.log"

    watcher._configure_logger(
        {
            "stdout": {
                "enabled": True,
                "level": "DEBUG",
                "colorize": False,
                "format": "stdout-format",
            },
            "stderr": {
                "enabled": True,
                "level": "ERROR",
                "colorize": True,
                "format": "stderr-format",
            },
            "file": {
                "enabled": True,
                "path": str(log_path),
                "level": "WARNING",
                "rotation": "1 day",
                "compression": "gz",
                "retention": "30 days",
                "format": "file-format",
            },
        }
    )

    assert fake_logger.remove_calls == 1
    assert len(fake_logger.add_calls) == 3

    stdout_call = fake_logger.add_calls[0]
    assert stdout_call["sink"] is ed_app_logging.sys.stdout
    assert stdout_call["level"] == "DEBUG"
    assert stdout_call["colorize"] is False
    assert stdout_call["format"] == "stdout-format"
    assert stdout_call["enqueue"] is True

    stderr_call = fake_logger.add_calls[1]
    assert stderr_call["sink"] is ed_app_logging.sys.stderr
    assert stderr_call["level"] == "ERROR"

    file_call = fake_logger.add_calls[2]
    assert file_call["sink"] == str(log_path)
    assert file_call["level"] == "WARNING"
    assert file_call["rotation"] == "1 day"
    assert file_call["format"] == "file-format"
    assert callable(file_call["filter"])
    assert log_path.parent.is_dir() is True


def test_configure_logger_can_disable_console_and_file(
    tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "config.json")
    watcher._configure_logger(
        {
            "stdout": {"enabled": False},
            "stderr": {"enabled": False},
            "file": {"enabled": False},
        }
    )

    assert fake_logger.remove_calls == 1
    assert not fake_logger.add_calls


def test_configure_logger_runs_archive_housekeeping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "config.json")
    log_path = tmp_path / "logs" / "app.log"
    archive_calls: list[tuple[Path, Path, int]] = []
    delete_calls: list[tuple[Path, int]] = []

    monkeypatch.setattr(
        ed_app_logging,
        "_archive_stale_logs",
        lambda log_path_arg, archive_dir_arg, archive_after_days: archive_calls.append(
            (log_path_arg, archive_dir_arg, archive_after_days)
        ),
    )
    monkeypatch.setattr(
        ed_app_logging,
        "_delete_expired_archives",
        lambda archive_dir_arg, archive_retention_days: delete_calls.append(
            (archive_dir_arg, archive_retention_days)
        ),
    )

    watcher._configure_logger(
        {
            "stdout": {"enabled": False},
            "stderr": {"enabled": False},
            "file": {
                "enabled": True,
                "path": str(log_path),
                "level": "INFO",
                "rotation": "1 day",
                "archive_dir": str(tmp_path / "logs" / "archive"),
                "archive_after_days": 7,
                "archive_retention_days": 30,
                "format": "file-format",
            },
        }
    )

    file_call = fake_logger.add_calls[0]
    assert "compression" not in file_call
    assert "retention" not in file_call
    assert archive_calls == [
        (
            log_path.resolve(),
            (tmp_path / "logs" / "archive").resolve(),
            7,
        )
    ]
    assert delete_calls == [(((tmp_path / "logs" / "archive").resolve()), 30)]
    assert log_path.parent.is_dir() is True


def test_event_targets_config_checks_source_and_dest_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    watcher = ed_app_logging._LoguruConfigWatcher(config_path)

    assert watcher._event_targets_config(FileModifiedEvent(str(config_path))) is True
    assert (
        watcher._event_targets_config(
            FileMovedEvent(str(tmp_path / "other.json"), str(config_path))
        )
        is True
    )
    assert (
        watcher._event_targets_config(FileCreatedEvent(str(tmp_path / "other.json")))
        is False
    )


def test_event_targets_config_returns_false_when_event_has_no_dest_path(
    tmp_path: Path,
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "loguru.json")

    class Event:
        src_path = str(tmp_path / "other.json")

    assert watcher._event_targets_config(Event()) is False


def test_handle_fs_event_applies_only_for_targeted_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "loguru.json"
    watcher = ed_app_logging._LoguruConfigWatcher(config_path)
    apply_calls: list[bool] = []

    def record_apply(force: bool) -> None:
        apply_calls.append(force)

    monkeypatch.setattr(watcher, "_apply_if_needed", record_apply)

    watcher.handle_fs_event(FileDeletedEvent(str(tmp_path / "other.json")))
    watcher.handle_fs_event(FileModifiedEvent(str(config_path)))

    assert apply_calls == [False]


def test_apply_if_needed_skips_when_mtime_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "loguru.json"
    config_path.write_text("{}", encoding="utf-8")
    watcher = ed_app_logging._LoguruConfigWatcher(config_path)
    watcher._config_mtime_ns = config_path.stat().st_mtime_ns
    configure_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(watcher, "_load_config", lambda: {"console": {}, "file": {}})
    monkeypatch.setattr(watcher, "_configure_logger", configure_calls.append)

    watcher._apply_if_needed(force=False)

    assert not configure_calls


def test_apply_if_needed_handles_missing_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "missing.json")
    configured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        watcher, "_load_config", lambda: {"console": {}, "file": {}, "watch": {}}
    )
    monkeypatch.setattr(watcher, "_configure_logger", configured.append)

    watcher._apply_if_needed(force=True)

    assert configured == [{"console": {}, "file": {}, "watch": {}}]
    assert watcher._config_mtime_ns is None
    assert (
        ("Reloaded Loguru configuration from {}", watcher.config_path),
        {},
    ) in fake_logger.calls_for("debug")


def test_apply_if_needed_reloads_and_updates_mtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    config_path = tmp_path / "loguru.json"
    config_path.write_text("{}", encoding="utf-8")
    watcher = ed_app_logging._LoguruConfigWatcher(config_path)
    configured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        watcher, "_load_config", lambda: {"console": {}, "file": {}, "watch": {}}
    )
    monkeypatch.setattr(watcher, "_configure_logger", configured.append)

    watcher._apply_if_needed(force=True)

    assert configured == [{"console": {}, "file": {}, "watch": {}}]
    assert watcher._config_mtime_ns == config_path.stat().st_mtime_ns
    assert (
        ("Reloaded Loguru configuration from {}", watcher.config_path),
        {},
    ) in fake_logger.calls_for("debug")


def test_start_configures_and_starts_observer_when_watch_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    config_path = tmp_path / "config" / "loguru.json"
    watcher = ed_app_logging._LoguruConfigWatcher(config_path)
    observer = FakeObserver()
    apply_calls: list[bool] = []

    def record_apply(force: bool) -> None:
        apply_calls.append(force)

    monkeypatch.setattr(watcher, "_apply_if_needed", record_apply)
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": True}, "stdout": {}, "stderr": {}, "file": {}},
    )
    monkeypatch.setattr(ed_app_logging, "Observer", lambda: observer)

    watcher.start()

    assert apply_calls == [True]
    assert len(observer.schedule_calls) == 1
    handler, path, recursive = observer.schedule_calls[0]
    assert isinstance(handler, ed_app_logging._ConfigFileEventHandler)
    assert path == str(config_path.parent.resolve())
    assert not recursive
    assert observer.started
    assert watcher._observer is observer
    assert (
        ("Started watchdog observer for {}", watcher.config_path),
        {},
    ) in fake_logger.calls_for("debug")


def test_start_skips_observer_when_watch_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "loguru.json")
    apply_calls: list[bool] = []

    def record_apply(force: bool) -> None:
        apply_calls.append(force)

    monkeypatch.setattr(watcher, "_apply_if_needed", record_apply)
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": False}, "stdout": {}, "stderr": {}, "file": {}},
    )

    watcher.start()

    assert apply_calls == [True]
    assert watcher._observer is None


def test_start_does_not_create_duplicate_observers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watcher = ed_app_logging._LoguruConfigWatcher(tmp_path / "loguru.json")
    watcher._observer = FakeObserver()
    observer_factory_calls = 0

    def fake_observer() -> FakeObserver:
        nonlocal observer_factory_calls
        observer_factory_calls += 1
        return FakeObserver()

    monkeypatch.setattr(watcher, "_apply_if_needed", lambda force: None)
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": True}, "stdout": {}, "stderr": {}, "file": {}},
    )
    monkeypatch.setattr(ed_app_logging, "Observer", fake_observer)

    watcher.start()

    assert observer_factory_calls == 0


def test_config_file_event_handler_forwards_all_event_types(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    handled: list[str] = []

    class Watcher:
        def handle_fs_event(self, event: Any) -> None:
            handled.append(type(event).__name__)

    handler = ed_app_logging._ConfigFileEventHandler(Watcher())
    handler.on_modified(FileModifiedEvent(str(config_path)))
    handler.on_created(FileCreatedEvent(str(config_path)))
    handler.on_deleted(FileDeletedEvent(str(config_path)))
    handler.on_moved(FileMovedEvent(str(config_path), str(tmp_path / "next.json")))

    assert handled == [
        "FileModifiedEvent",
        "FileCreatedEvent",
        "FileDeletedEvent",
        "FileMovedEvent",
    ]


def test_initialize_watcher_loads_env_and_starts_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    created_paths: list[Path] = []
    start_calls = 0
    load_dotenv_calls = 0

    class FakeWatcher:
        def __init__(self, config_path: Path) -> None:
            created_paths.append(Path(config_path))

        def start(self) -> None:
            nonlocal start_calls
            start_calls += 1

    def _count() -> None:
        nonlocal load_dotenv_calls
        load_dotenv_calls += 1

    monkeypatch.setattr(ed_app_logging, "load_dotenv", _count)
    monkeypatch.setattr(ed_app_logging, "_LoguruConfigWatcher", FakeWatcher)

    config_path = tmp_path / "loguru.json"
    ed_app_logging.configure_logging(config_path)
    ed_app_logging.configure_logging(tmp_path / "other.json")

    assert created_paths == [config_path]
    assert start_calls == 1
    assert load_dotenv_calls == 2


def test_configure_logging_is_thread_safe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    created_paths: list[Path] = []
    barrier = threading.Barrier(6)
    watchers: list[object] = []

    class FakeWatcher:
        def __init__(self, config_path: Path) -> None:
            time.sleep(0.02)
            created_paths.append(Path(config_path))
            watchers.append(self)

        def start(self) -> None:
            return None

    monkeypatch.setattr(ed_app_logging, "_LoguruConfigWatcher", FakeWatcher)
    monkeypatch.setattr(ed_app_logging, "load_dotenv", lambda: None)

    def worker(index: int) -> None:
        barrier.wait()
        ed_app_logging.configure_logging(tmp_path / f"{index}.json")

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(created_paths) == 1
    assert created_paths[0].parent == tmp_path
    assert len(watchers) == 1


def test_test_module_main_is_a_noop() -> None:
    main()
