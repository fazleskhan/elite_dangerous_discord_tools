import asyncio
import gzip
import json
import os
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

import ed_logging_utils


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
            self.add_calls.append({"sink": sink, **kwargs})
            return len(self.add_calls)

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
    monkeypatch.setattr(ed_logging_utils, "_WATCHER", None)
    monkeypatch.setattr(ed_logging_utils.EDLoggingUtils, "_instance", None)


@pytest.fixture()
def fake_logger(monkeypatch: pytest.MonkeyPatch) -> FakeSinkLogger:
    logger = FakeSinkLogger()
    monkeypatch.setattr(ed_logging_utils, "_logger", logger)
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

    merged = ed_logging_utils._LoguruConfigWatcher._merge_dict(base, override)

    assert merged == {
        "console": {"enabled": True, "level": "DEBUG"},
        "file": {"enabled": True, "path": "logs/app.log"},
        "watch": {"enabled": False},
    }


def test_load_config_returns_defaults_and_ignores_invalid_json(tmp_path: Path) -> None:
    missing_watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "missing.json")
    assert missing_watcher._load_config()["console"]["level"] == "INFO"

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{ invalid", encoding="utf-8")
    invalid_watcher = ed_logging_utils._LoguruConfigWatcher(invalid_path)

    assert invalid_watcher._load_config()["file"]["path"] == "logs/application.log"


def test_load_config_merges_user_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    config_path.write_text(
        json.dumps(
            {
                "console": {"level": "DEBUG"},
                "file": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)
    loaded = watcher._load_config()

    assert loaded["console"]["level"] == "DEBUG"
    assert loaded["console"]["enabled"] is True
    assert loaded["file"]["enabled"] is False
    assert loaded["watch"]["enabled"] is True


def test_configure_logger_adds_console_and_file_sinks(
    tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "config.json")
    archive_dir = tmp_path / "archive"
    log_path = tmp_path / "logs" / "app.log"

    watcher._configure_logger(
        {
            "console": {
                "enabled": True,
                "level": "DEBUG",
                "colorize": False,
                "format": "console-format",
            },
            "file": {
                "enabled": True,
                "path": str(log_path),
                "level": "WARNING",
                "rotation": "1 day",
                "retention_days": 3,
                "archive_directory": str(archive_dir),
                "format": "file-format",
            },
        }
    )

    assert fake_logger.remove_calls == 1
    assert len(fake_logger.add_calls) == 2

    console_call = fake_logger.add_calls[0]
    assert console_call["sink"] is ed_logging_utils.sys.stderr
    assert console_call["level"] == "DEBUG"
    assert console_call["colorize"] is False
    assert console_call["format"] == "console-format"
    assert console_call["enqueue"] is True

    file_call = fake_logger.add_calls[1]
    assert file_call["sink"] == str(log_path)
    assert file_call["level"] == "WARNING"
    assert file_call["rotation"] == "1 day"
    assert file_call["format"] == "file-format"
    assert callable(file_call["retention"])
    assert callable(file_call["compression"])
    assert log_path.parent.is_dir() is True
    assert archive_dir.is_dir() is True


def test_configure_logger_can_disable_console_and_file(
    tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "config.json")
    watcher._configure_logger(
        {
            "console": {"enabled": False},
            "file": {"enabled": False},
        }
    )

    assert fake_logger.remove_calls == 1
    assert fake_logger.add_calls == []


def test_compress_to_archive_factory_gzips_and_removes_source(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    source = tmp_path / "application.log.1"
    source.write_text("hello log", encoding="utf-8")

    compress = ed_logging_utils._LoguruConfigWatcher._compress_to_archive_factory(
        archive_dir
    )
    compress(str(source))

    archive_path = archive_dir / "application.log.1.gz"
    assert source.exists() is False
    assert archive_path.exists() is True
    with gzip.open(archive_path, "rt", encoding="utf-8") as handle:
        assert handle.read() == "hello log"


def test_retention_cleanup_prunes_old_logs_and_archives(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    current_log = tmp_path / "current.log"
    old_log = tmp_path / "old.log"
    recent_archive = archive_dir / "recent.log.gz"
    old_archive = archive_dir / "old.log.gz"

    current_log.write_text("recent", encoding="utf-8")
    old_log.write_text("old", encoding="utf-8")
    archive_dir.mkdir(parents=True, exist_ok=True)
    recent_archive.write_text("recent archive", encoding="utf-8")
    old_archive.write_text("old archive", encoding="utf-8")

    now = time.time()
    two_days = 2 * 24 * 60 * 60
    one_hour = 60 * 60
    old_time = now - two_days
    recent_time = now - one_hour

    for path in [old_log, old_archive]:
        os.utime(path, times=(old_time, old_time))

    for path in [current_log, recent_archive]:
        os.utime(path, times=(recent_time, recent_time))

    cleanup = ed_logging_utils._LoguruConfigWatcher._retention_cleanup(archive_dir, 1)
    cleanup([str(current_log), str(old_log), str(tmp_path / "missing.log")])

    assert current_log.exists() is True
    assert old_log.exists() is False
    assert recent_archive.exists() is True
    assert old_archive.exists() is False


def test_retention_cleanup_ignores_races_when_files_disappear(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    active_log = tmp_path / "active.log"
    active_log.write_text("active", encoding="utf-8")

    archived_file = archive_dir / "rotated.log.gz"
    archived_file.write_text("archive", encoding="utf-8")

    real_stat = Path.stat
    real_glob = Path.glob

    def fake_stat(self: Path) -> os.stat_result:
        if self == active_log or self == archived_file:
            raise FileNotFoundError
        return real_stat(self)

    def fake_glob(self: Path, pattern: str):  # type: ignore[no-untyped-def]
        if self == archive_dir and pattern == "*.gz":
            return [archived_file]
        return list(real_glob(self, pattern))

    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(Path, "glob", fake_glob)

    cleanup = ed_logging_utils._LoguruConfigWatcher._retention_cleanup(archive_dir, 1)
    cleanup([str(active_log)])


def test_event_targets_config_checks_source_and_dest_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)

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
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "loguru.json")

    class Event:
        src_path = str(tmp_path / "other.json")

    assert watcher._event_targets_config(Event()) is False


def test_handle_fs_event_applies_only_for_targeted_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "loguru.json"
    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)
    apply_calls: list[bool] = []

    monkeypatch.setattr(
        watcher, "_apply_if_needed", lambda force: apply_calls.append(force)
    )

    watcher.handle_fs_event(FileDeletedEvent(str(tmp_path / "other.json")))
    watcher.handle_fs_event(FileModifiedEvent(str(config_path)))

    assert apply_calls == [False]


def test_apply_if_needed_skips_when_mtime_is_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "loguru.json"
    config_path.write_text("{}", encoding="utf-8")
    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)
    watcher._config_mtime_ns = config_path.stat().st_mtime_ns
    configure_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(watcher, "_load_config", lambda: {"console": {}, "file": {}})
    monkeypatch.setattr(
        watcher, "_configure_logger", lambda config: configure_calls.append(config)
    )

    watcher._apply_if_needed(force=False)

    assert configure_calls == []


def test_apply_if_needed_handles_missing_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_logger: FakeSinkLogger
) -> None:
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "missing.json")
    configured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        watcher, "_load_config", lambda: {"console": {}, "file": {}, "watch": {}}
    )
    monkeypatch.setattr(
        watcher, "_configure_logger", lambda config: configured.append(config)
    )

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
    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)
    configured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        watcher, "_load_config", lambda: {"console": {}, "file": {}, "watch": {}}
    )
    monkeypatch.setattr(
        watcher, "_configure_logger", lambda config: configured.append(config)
    )

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
    watcher = ed_logging_utils._LoguruConfigWatcher(config_path)
    observer = FakeObserver()
    apply_calls: list[bool] = []

    monkeypatch.setattr(
        watcher, "_apply_if_needed", lambda force: apply_calls.append(force)
    )
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": True}, "console": {}, "file": {}},
    )
    monkeypatch.setattr(ed_logging_utils, "Observer", lambda: observer)

    watcher.start()

    assert apply_calls == [True]
    assert len(observer.schedule_calls) == 1
    handler, path, recursive = observer.schedule_calls[0]
    assert isinstance(handler, ed_logging_utils._ConfigFileEventHandler)
    assert path == str(config_path.parent.resolve())
    assert recursive is False
    assert observer.started is True
    assert watcher._observer is observer
    assert (
        ("Started watchdog observer for {}", watcher.config_path),
        {},
    ) in fake_logger.calls_for("debug")


def test_start_skips_observer_when_watch_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "loguru.json")
    apply_calls: list[bool] = []

    monkeypatch.setattr(
        watcher, "_apply_if_needed", lambda force: apply_calls.append(force)
    )
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": False}, "console": {}, "file": {}},
    )

    watcher.start()

    assert apply_calls == [True]
    assert watcher._observer is None


def test_start_does_not_create_duplicate_observers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watcher = ed_logging_utils._LoguruConfigWatcher(tmp_path / "loguru.json")
    watcher._observer = FakeObserver()  # type: ignore[assignment]
    observer_factory_calls = 0

    def fake_observer() -> FakeObserver:
        nonlocal observer_factory_calls
        observer_factory_calls += 1
        return FakeObserver()

    monkeypatch.setattr(watcher, "_apply_if_needed", lambda force: None)
    monkeypatch.setattr(
        watcher,
        "_load_config",
        lambda: {"watch": {"enabled": True}, "console": {}, "file": {}},
    )
    monkeypatch.setattr(ed_logging_utils, "Observer", fake_observer)

    watcher.start()

    assert observer_factory_calls == 0


def test_config_file_event_handler_forwards_all_event_types(tmp_path: Path) -> None:
    config_path = tmp_path / "loguru.json"
    handled: list[str] = []

    class Watcher:
        def handle_fs_event(self, event: Any) -> None:
            handled.append(type(event).__name__)

    handler = ed_logging_utils._ConfigFileEventHandler(Watcher())  # type: ignore[arg-type]
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

    monkeypatch.setattr(ed_logging_utils, "load_dotenv", lambda: _count())
    monkeypatch.setattr(ed_logging_utils, "_LoguruConfigWatcher", FakeWatcher)

    def _count() -> None:
        nonlocal load_dotenv_calls
        load_dotenv_calls += 1

    config_path = tmp_path / "loguru.json"
    ed_logging_utils.EDLoggingUtils._initialize_watcher(config_path)
    ed_logging_utils.EDLoggingUtils._initialize_watcher(tmp_path / "other.json")

    assert created_paths == [config_path]
    assert start_calls == 1
    assert load_dotenv_calls == 2


def test_create_returns_singleton_and_initializes_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    init_calls: list[Path] = []

    monkeypatch.setattr(
        ed_logging_utils.EDLoggingUtils,
        "_initialize_watcher",
        lambda config_path: init_calls.append(Path(config_path)),
    )

    first = ed_logging_utils.EDLoggingUtils.create(tmp_path / "first.json")
    second = ed_logging_utils.EDLoggingUtils.create(tmp_path / "second.json")

    assert first is second
    assert init_calls == [tmp_path / "first.json"]


def test_create_is_thread_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_calls: list[Path] = []
    barrier = threading.Barrier(6)
    instances: list[ed_logging_utils.EDLoggingUtils] = []
    instances_lock = threading.Lock()

    def fake_initialize(config_path: Path) -> None:
        time.sleep(0.02)
        init_calls.append(Path(config_path))

    monkeypatch.setattr(
        ed_logging_utils.EDLoggingUtils, "_initialize_watcher", fake_initialize
    )

    def worker(index: int) -> None:
        barrier.wait()
        instance = ed_logging_utils.EDLoggingUtils.create(tmp_path / f"{index}.json")
        with instances_lock:
            instances.append(instance)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(instances) == 6
    assert len({id(instance) for instance in instances}) == 1
    assert len(init_calls) == 1


def test_logging_methods_delegate_to_underlying_logger(
    fake_logger: FakeSinkLogger,
) -> None:
    logging_utils = ed_logging_utils.EDLoggingUtils("config/loguru.json")

    logging_utils.debug("debug {}", 1)
    logging_utils.info("info {}", 2)
    logging_utils.warning("warn {}", 3)
    logging_utils.error("error {}", 4)
    logging_utils.exception("exception {}", 5)

    assert ("debug {}", 1) == fake_logger.calls_for("debug")[0][0]
    assert ("info {}", 2) == fake_logger.calls_for("info")[0][0]
    assert ("warn {}", 3) == fake_logger.calls_for("warning")[0][0]
    assert ("error {}", 4) == fake_logger.calls_for("error")[0][0]
    assert ("exception {}", 5) == fake_logger.calls_for("exception")[0][0]


def test_opt_delegates_to_underlying_logger(fake_logger: FakeSinkLogger) -> None:
    logging_utils = ed_logging_utils.EDLoggingUtils("config/loguru.json")

    result = logging_utils.opt(depth=1)

    assert result == "opt-result"
    assert fake_logger.opt_calls == [((), {"depth": 1})]


@pytest.mark.asyncio
async def test_logging_methods_work_inside_asyncio(fake_logger: FakeSinkLogger) -> None:
    logging_utils = ed_logging_utils.EDLoggingUtils("config/loguru.json")

    async def worker(name: str) -> None:
        await asyncio.sleep(0)
        logging_utils.info("async {}", name)

    await asyncio.gather(*(worker(f"task-{index}") for index in range(10)))

    logged_names = {args[1] for args, _ in fake_logger.calls_for("info")}
    assert logged_names == {f"task-{index}" for index in range(10)}


def test_logging_calls_are_thread_safe_under_contention(
    fake_logger: FakeSinkLogger,
) -> None:
    logging_utils = ed_logging_utils.EDLoggingUtils("config/loguru.json")
    barrier = threading.Barrier(5)

    def worker(index: int) -> None:
        barrier.wait()
        for offset in range(30):
            logging_utils.debug("thread {}", index * 30 + offset)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    debug_calls = fake_logger.calls_for("debug")
    assert len(debug_calls) == 150
    assert len({args[1] for args, _ in debug_calls}) == 150


def test_test_module_main_is_a_noop() -> None:
    assert main() is None
