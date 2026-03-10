import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import ed_tinydb
from ed_constants import (
    default_tinydb_name,
    system_info_name_field,
    system_info_neighbors_field,
    tinydb_name_env,
    value_key,
)


def main() -> None: ...


class ThreadSafeLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[tuple[str, str, tuple[Any, ...]]] = []

    def _record(self, level: str, message: str, args: tuple[Any, ...]) -> None:
        with self._lock:
            self.calls.append((level, message, args))

    def debug(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("debug", message, args)

    def info(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("info", message, args)

    def warning(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("warning", message, args)

    def error(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("error", message, args)

    def exception(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("exception", message, args)

    def opt(self, *args: Any, **kwargs: Any) -> "ThreadSafeLogger":
        return self

    def messages(self, level: str) -> list[tuple[str, tuple[Any, ...]]]:
        with self._lock:
            return [
                (message, args)
                for call_level, message, args in self.calls
                if call_level == level
            ]


@pytest.fixture()
def logger() -> ThreadSafeLogger:
    return ThreadSafeLogger()


@pytest.fixture()
def sample_system() -> dict[str, Any]:
    return {
        "name": "Sol",
        "id64": 1,
        "coords": {"x": 0, "y": 0, "z": 0},
    }


@pytest.fixture()
def sample_neighbors() -> list[dict[str, Any]]:
    return [
        {"name": "Alpha Centauri", "id64": 2},
        {"name": "Barnard's Star", "id64": 3},
    ]


@pytest.fixture()
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "ed_route.json"


@pytest.fixture()
def tinydb_backend(
    database_path: Path, logger: ThreadSafeLogger
) -> ed_tinydb.EDTinyDB:
    return ed_tinydb.EDTinyDB(str(database_path), logging_utils=logger)


@pytest.mark.asyncio
async def test_aiotinydb_requires_async_context(tmp_path: Path) -> None:
    db = ed_tinydb.AIOTinyDB(str(tmp_path / "async.json"))

    with pytest.raises(RuntimeError, match="must be used within 'async with'"):
        await db.all()


@pytest.mark.asyncio
async def test_aiotinydb_crud_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "async.json"
    system = {"name": "Sol", "id64": 1}

    async with ed_tinydb.AIOTinyDB(str(database_path)) as db:
        system_query = ed_tinydb.Query()
        assert await db.contains(system_query.name == "Sol") is False
        inserted_id = await db.insert(system)
        assert inserted_id == 1
        assert await db.contains(system_query.name == "Sol") is True
        assert await db.get(system_query.name == "Sol") == system
        assert await db.update({"neighbors": [{"name": "Lave"}]}, system_query.name == "Sol") == [1]
        assert await db.all() == [{"name": "Sol", "id64": 1, "neighbors": [{"name": "Lave"}]}]


def test_smartcache_tinydb_uses_smartcache_table() -> None:
    assert ed_tinydb.SmartCacheTinyDB.table_class.__name__ == "SmartCacheTable"


def test_create_uses_explicit_name_then_env_then_default(
    monkeypatch: pytest.MonkeyPatch, logger: ThreadSafeLogger, tmp_path: Path
) -> None:
    explicit = ed_tinydb.EDTinyDB.create(
        logging_utils=logger,
        datasource_name=str(tmp_path / "explicit.json"),
    )
    assert explicit.datasource_name.endswith("explicit.json")

    monkeypatch.setenv(tinydb_name_env, str(tmp_path / "env.json"))
    from_env = ed_tinydb.EDTinyDB.create(logging_utils=logger)
    assert from_env.datasource_name.endswith("env.json")

    monkeypatch.delenv(tinydb_name_env, raising=False)
    defaulted = ed_tinydb.EDTinyDB.create(logging_utils=logger)
    assert defaulted.datasource_name == default_tinydb_name


def test_constructor_validates_inputs_and_logs_backend(logger: ThreadSafeLogger) -> None:
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        ed_tinydb.EDTinyDB("ignored.json", logging_utils=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="datasource_name of type str is required"):
        ed_tinydb.EDTinyDB(None, logging_utils=logger)  # type: ignore[arg-type]

    backend = ed_tinydb.EDTinyDB("./data/test.json", logging_utils=logger)
    assert backend.datasource_name == "./data/test.json"
    assert ("aiotinydb backend", ()) in logger.messages("info")


def test_run_async_handles_plain_calls_and_existing_event_loop(
    tinydb_backend: ed_tinydb.EDTinyDB,
) -> None:
    async def returns_value() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert tinydb_backend._run_async(returns_value()) == "ok"

    async def run_inside_loop() -> str:
        return tinydb_backend._run_async(returns_value())

    assert asyncio.run(run_inside_loop()) == "ok"


def test_run_async_propagates_worker_thread_exceptions(
    tinydb_backend: ed_tinydb.EDTinyDB,
) -> None:
    async def raises() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    async def run_inside_loop() -> None:
        tinydb_backend._run_async(raises())

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_inside_loop())


def test_insert_get_add_neighbors_and_cache_round_trip(
    tinydb_backend: ed_tinydb.EDTinyDB,
    sample_system: dict[str, Any],
    sample_neighbors: list[dict[str, Any]],
) -> None:
    tinydb_backend.insert_system(sample_system)
    tinydb_backend.insert_system(sample_system)

    fetched = tinydb_backend.get_system("Sol")
    assert fetched == sample_system

    tinydb_backend.add_neighbors(sample_system, sample_neighbors)
    updated = tinydb_backend.get_system("Sol")

    assert updated is not None
    assert updated[system_info_neighbors_field] == sample_neighbors
    assert [system["name"] for system in tinydb_backend.get_all_systems()] == ["Sol"]

    debug_messages = tinydb_backend.logger.messages("debug")
    assert ("Inserted system={} doc_id={}", ("Sol", 1)) in debug_messages
    assert (
        "Updated neighbors for system={} updated_rows={}",
        ("Sol", 1),
    ) in debug_messages


def test_insert_system_ignores_missing_name_and_cached_entries(
    tinydb_backend: ed_tinydb.EDTinyDB,
) -> None:
    run_async_calls: list[Any] = []

    def fake_run_async(coro: Any) -> Any:
        run_async_calls.append(coro)
        if hasattr(coro, "close"):
            coro.close()
        return True

    tinydb_backend._run_async = fake_run_async  # type: ignore[method-assign]

    tinydb_backend.insert_system({"id64": 1})
    tinydb_backend._cache_set("Sol", {"name": "Sol"})
    tinydb_backend.insert_system({"name": "Sol", "id64": 1})

    assert run_async_calls == []


def test_get_system_returns_none_and_logs_exception_on_lookup_failure(
    tinydb_backend: ed_tinydb.EDTinyDB,
) -> None:
    def fake_run_async(coro: Any) -> Any:
        if hasattr(coro, "close"):
            coro.close()
        raise RuntimeError("db failed")

    tinydb_backend._run_async = fake_run_async  # type: ignore[method-assign]

    assert tinydb_backend.get_system("Sol") is None
    assert ("Lookup failed for system={}", ("Sol",)) in tinydb_backend.logger.messages(
        "exception"
    )


def test_get_all_systems_populates_cache_and_reuses_it(
    tinydb_backend: ed_tinydb.EDTinyDB,
    sample_system: dict[str, Any],
) -> None:
    systems = [sample_system, {"name": "Lave", "id64": 2}]
    run_async_calls = 0

    def fake_run_async(coro: Any) -> Any:
        nonlocal run_async_calls
        run_async_calls += 1
        if hasattr(coro, "close"):
            coro.close()
        return systems

    tinydb_backend._run_async = fake_run_async  # type: ignore[method-assign]

    assert tinydb_backend.get_all_systems() == systems
    assert tinydb_backend.get_all_systems() == systems
    assert tinydb_backend.get_system("Lave") == {"name": "Lave", "id64": 2}
    assert run_async_calls == 1


def test_init_and_import_datasource_load_sorted_json_records(
    tmp_path: Path, logger: ThreadSafeLogger
) -> None:
    database_path = tmp_path / "db" / "target.json"
    import_dir = tmp_path / "import"
    import_dir.mkdir(parents=True)
    (import_dir / "b.json").write_text('{"name":"Lave","id64":2}', encoding="utf-8")
    (import_dir / "a.json").write_text(
        '[{"name":"Sol","id64":1},"ignore-me",{"name":"Achenar","id64":3}]',
        encoding="utf-8",
    )
    (import_dir / "notes.txt").write_text("skip", encoding="utf-8")

    backend = ed_tinydb.EDTinyDB(str(database_path), logging_utils=logger)
    inserted: list[dict[str, Any]] = []
    backend.insert_system = inserted.append  # type: ignore[method-assign]

    backend.init_datasource(str(import_dir))

    assert [entry["name"] for entry in inserted] == ["Sol", "Achenar", "Lave"]
    assert ("Importing TinyDB datasource from {} JSON files in {}", (2, str(import_dir))) in logger.messages("info")


def test_import_datasource_requires_existing_directory(
    tinydb_backend: ed_tinydb.EDTinyDB, tmp_path: Path
) -> None:
    with pytest.raises(FileNotFoundError, match="Import directory does not exist"):
        tinydb_backend.import_datasource(str(tmp_path / "missing"))


def test_export_datasource_writes_safe_sorted_json_files(
    tmp_path: Path, logger: ThreadSafeLogger, sample_neighbors: list[dict[str, Any]]
) -> None:
    backend = ed_tinydb.EDTinyDB(str(tmp_path / "db" / "target.json"), logging_utils=logger)
    export_dir = tmp_path / "export"
    exported_systems = [
        {"name": "Alpha/Beta"},
        {"name": ""},
        {"id64": 3},
    ]
    full_record = {"name": "Alpha/Beta", "id64": 1, "neighbors": sample_neighbors}

    backend.get_all_systems = lambda: exported_systems  # type: ignore[method-assign]
    backend.get_system = lambda name: full_record if name == "Alpha/Beta" else None  # type: ignore[method-assign]

    backend.export_datasource(str(export_dir))

    exported_file = export_dir / "Alpha_Beta.json"
    assert exported_file.exists()
    assert json.loads(exported_file.read_text(encoding="utf-8")) == full_record
    assert backend._safe_filename("Alpha/Beta:*?") == "Alpha_Beta___"


def test_write_lock_serializes_concurrent_insert_and_neighbor_updates(
    tinydb_backend: ed_tinydb.EDTinyDB,
    sample_system: dict[str, Any],
    sample_neighbors: list[dict[str, Any]],
) -> None:
    barrier = threading.Barrier(2)
    tracker_lock = threading.Lock()
    active_writes = 0
    max_active_writes = 0
    call_count = 0

    def fake_run_async(coro: Any) -> Any:
        nonlocal active_writes, max_active_writes, call_count
        with tracker_lock:
            call_count += 1
            active_writes += 1
            max_active_writes = max(max_active_writes, active_writes)

        time.sleep(0.05)

        with tracker_lock:
            active_writes -= 1

        if hasattr(coro, "close"):
            coro.close()
        return True if "insert_system_async" in repr(coro) else None

    tinydb_backend._run_async = fake_run_async  # type: ignore[method-assign]

    def do_insert() -> None:
        barrier.wait()
        tinydb_backend.insert_system(sample_system)

    def do_add_neighbors() -> None:
        barrier.wait()
        tinydb_backend.add_neighbors(sample_system, sample_neighbors)

    insert_thread = threading.Thread(target=do_insert)
    add_neighbors_thread = threading.Thread(target=do_add_neighbors)
    insert_thread.start()
    add_neighbors_thread.start()
    insert_thread.join()
    add_neighbors_thread.join()

    assert call_count == 2
    assert max_active_writes == 1
    cached_sol = tinydb_backend.get_system("Sol")
    assert cached_sol in (
        sample_system,
        {
            **sample_system,
            system_info_neighbors_field: sample_neighbors,
        },
    )


def test_logging_remains_consistent_under_multithreaded_reads(
    tinydb_backend: ed_tinydb.EDTinyDB,
    sample_system: dict[str, Any],
) -> None:
    tinydb_backend.insert_system(sample_system)
    results: list[dict[str, Any] | None] = []
    results_lock = threading.Lock()

    def lookup() -> None:
        for _ in range(10):
            result = tinydb_backend.get_system("Sol")
            with results_lock:
                results.append(result)

    threads = [threading.Thread(target=lookup) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [sample_system] * 40
    assert tinydb_backend.logger.messages("exception") == []


if __name__ == "__main__":
    main()
