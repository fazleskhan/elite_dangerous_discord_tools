import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import ed_redis
from ed_constants import (
    default_redis_store_name,
    redis_app_name_env,
    redis_max_connections_env,
    redis_name,
    redis_url_env,
    system_info_name_field,
    system_info_neighbors_field,
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


class FakeRedisStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.strings: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    def exists(self, key: str) -> int:
        with self._lock:
            return 1 if key in self.strings else 0

    def set(self, key: str, value: str) -> bool:
        with self._lock:
            self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        with self._lock:
            return self.strings.get(key)

    def sadd(self, key: str, member: str) -> int:
        with self._lock:
            members = self.sets.setdefault(key, set())
            size_before = len(members)
            members.add(member)
            return len(members) - size_before

    def smembers(self, key: str) -> set[str]:
        with self._lock:
            return set(self.sets.get(key, set()))

    def mget(self, keys: list[str]) -> list[str | None]:
        with self._lock:
            return [self.strings.get(key) for key in keys]


class FakeRedisClient:
    def __init__(self, store: FakeRedisStore) -> None:
        self._store = store
        self.closed = False

    async def exists(self, key: str) -> int:
        return self._store.exists(key)

    async def set(self, key: str, value: str) -> bool:
        return self._store.set(key, value)

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def sadd(self, key: str, member: str) -> int:
        return self._store.sadd(key, member)

    async def smembers(self, key: str) -> set[str]:
        return self._store.smembers(key)

    async def mget(self, keys: list[str]) -> list[str | None]:
        return self._store.mget(keys)

    async def aclose(self) -> None:
        self.closed = True


class LegacyCloseRedisClient:
    def __init__(self, store: FakeRedisStore) -> None:
        self._store = store
        self.closed = False
        self.sync_close_calls = 0

    def close(self) -> None:
        self.sync_close_calls += 1
        self.closed = True


class CoroutineCloseRedisClient:
    def __init__(self, store: FakeRedisStore) -> None:
        self._store = store
        self.closed = False
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        self.closed = True


class FakeRedisFactory:
    def __init__(self, store: FakeRedisStore) -> None:
        self.store = store
        self.clients: list[FakeRedisClient] = []
        self.calls: list[dict[str, Any]] = []
        self.client_cls: type[FakeRedisClient] = FakeRedisClient

    def from_url(
        self,
        url: str,
        decode_responses: bool = False,
        max_connections: int | None = None,
    ) -> FakeRedisClient:
        self.calls.append(
            {
                "url": url,
                "decode_responses": decode_responses,
                "max_connections": max_connections,
            }
        )
        client = self.client_cls(self.store)
        self.clients.append(client)
        return client


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
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedisFactory:
    store = FakeRedisStore()
    factory = FakeRedisFactory(store)
    monkeypatch.setattr(ed_redis.redis, "from_url", factory.from_url)
    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 4)
    monkeypatch.setenv(redis_url_env, "redis://localhost:6379/0")
    monkeypatch.delenv(redis_max_connections_env, raising=False)
    return factory


@pytest.fixture()
def redis_backend(
    logger: ThreadSafeLogger, fake_redis: FakeRedisFactory
) -> ed_redis.EDRedis:
    return ed_redis.EDRedis.create(logging_utils=logger)


@pytest.mark.asyncio
async def test_close_client_async_prefers_aclose() -> None:
    client = FakeRedisClient(FakeRedisStore())
    await ed_redis.EDRedis(
        "test", "redis://localhost:6379/0", ThreadSafeLogger(), 1
    )._close_client_async(client)
    assert client.closed is True


@pytest.mark.asyncio
async def test_close_client_async_supports_legacy_sync_close() -> None:
    client = LegacyCloseRedisClient(FakeRedisStore())

    backend = ed_redis.EDRedis(
        "test", "redis://localhost:6379/0", ThreadSafeLogger(), 1
    )
    await backend._close_client_async(client)

    assert client.closed is True
    assert client.sync_close_calls == 1


@pytest.mark.asyncio
async def test_close_client_async_supports_legacy_coroutine_close() -> None:
    client = CoroutineCloseRedisClient(FakeRedisStore())

    backend = ed_redis.EDRedis(
        "test", "redis://localhost:6379/0", ThreadSafeLogger(), 1
    )
    await backend._close_client_async(client)

    assert client.closed is True
    assert client.close_calls == 1


def test_create_uses_explicit_name_then_env_then_default(
    monkeypatch: pytest.MonkeyPatch,
    logger: ThreadSafeLogger,
    fake_redis: FakeRedisFactory,
) -> None:
    explicit = ed_redis.EDRedis.create(
        logging_utils=logger,
        datasource_name="explicit-app",
        redis_url="redis://explicit:6379/0",
        max_connections=7,
    )
    assert explicit.datasource_name == "explicit-app"
    assert explicit._redis_url == "redis://explicit:6379/0"
    assert explicit._max_connections == 7

    monkeypatch.setenv(redis_app_name_env, "env-app")
    from_env = ed_redis.EDRedis.create(logging_utils=logger)
    assert from_env.datasource_name == "env-app"

    monkeypatch.delenv(redis_app_name_env, raising=False)
    defaulted = ed_redis.EDRedis.create(logging_utils=logger)
    assert defaulted.datasource_name == default_redis_store_name


def test_constructor_validates_inputs_and_logs_backend(
    logger: ThreadSafeLogger,
) -> None:
    with pytest.raises(
        ValueError, match="Redis URL of type str is a required argument"
    ):
        ed_redis.EDRedis("test", None, logger, 1)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_redis.EDRedis("test", "redis://localhost:6379/0", None, 1)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="datasource_name of type str is required"):
        ed_redis.EDRedis(None, "redis://localhost:6379/0", logger, 1)  # type: ignore[arg-type]

    backend = ed_redis.EDRedis("test", "redis://localhost:6379/0", logger, 1)
    assert backend.datasource_name == "test"
    assert ("Redis backend: {}", (redis_name,)) in logger.messages("info")


def test_default_max_connections_handles_cpu_count_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: None)
    assert ed_redis.EDRedis._default_max_connections() == 1

    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 0)
    assert ed_redis.EDRedis._default_max_connections() == 1

    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 6)
    assert ed_redis.EDRedis._default_max_connections() == 6


def test_resolve_redis_url_validates_supported_schemes_and_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(redis_url_env, raising=False)
    with pytest.raises(ValueError, match="REDIS_URL is required"):
        ed_redis.EDRedis._resolve_redis_url()

    with pytest.raises(ValueError, match="must use one of these schemes"):
        ed_redis.EDRedis._resolve_redis_url("http://localhost:6379/0")

    with pytest.raises(ValueError, match="must include a host"):
        ed_redis.EDRedis._resolve_redis_url("redis:///0")

    assert (
        ed_redis.EDRedis._resolve_redis_url("redis://localhost:6379/0")
        == "redis://localhost:6379/0"
    )
    assert (
        ed_redis.EDRedis._resolve_redis_url("rediss://localhost:6379/0")
        == "rediss://localhost:6379/0"
    )
    assert (
        ed_redis.EDRedis._resolve_redis_url("unix:///tmp/redis.sock")
        == "unix:///tmp/redis.sock"
    )


def test_run_async_handles_plain_calls_and_existing_event_loop(
    redis_backend: ed_redis.EDRedis,
) -> None:
    async def returns_value() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert redis_backend._run_async(returns_value()) == "ok"

    async def run_inside_loop() -> str:
        return redis_backend._run_async(returns_value())

    assert asyncio.run(run_inside_loop()) == "ok"


def test_run_async_propagates_worker_thread_exceptions(
    redis_backend: ed_redis.EDRedis,
) -> None:
    async def raises() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    async def run_inside_loop() -> None:
        redis_backend._run_async(raises())

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_inside_loop())


def test_insert_get_add_neighbors_and_get_all_systems_round_trip(
    redis_backend: ed_redis.EDRedis,
    logger: ThreadSafeLogger,
    sample_system: dict[str, Any],
    sample_neighbors: list[dict[str, Any]],
) -> None:
    second_system = {"name": "Lave", "id64": 4}

    redis_backend.insert_system(sample_system)
    redis_backend.insert_system(sample_system)
    redis_backend.insert_system(second_system)

    assert redis_backend.get_system("Sol") == sample_system

    redis_backend.add_neighbors(sample_system, sample_neighbors)
    updated = redis_backend.get_system("Sol")
    assert updated is not None
    assert updated[system_info_neighbors_field] == sample_neighbors

    systems = redis_backend.get_all_systems()
    assert [system[system_info_name_field] for system in systems] == ["Lave", "Sol"]

    debug_messages = logger.messages("debug")
    assert ("Inserted system={}", ("Sol",)) in debug_messages
    assert ("Skipped duplicate system insert for system={}", ("Sol",)) in debug_messages
    assert (
        "Updated neighbors for system={} updated_rows={}",
        ("Sol", 1),
    ) in debug_messages
    assert ("Loaded all systems count={}", (2,)) in debug_messages


def test_get_system_returns_none_for_missing_record_and_logs_lookup(
    redis_backend: ed_redis.EDRedis, logger: ThreadSafeLogger
) -> None:
    assert redis_backend.get_system("Missing") is None
    assert ("Lookup system={} found=False", ("Missing",)) in logger.messages("debug")


def test_get_system_logs_exception_on_lookup_failure(
    redis_backend: ed_redis.EDRedis, logger: ThreadSafeLogger
) -> None:
    def fake_run_async(coro: Any) -> Any:
        if hasattr(coro, "close"):
            coro.close()
        raise RuntimeError("lookup failed")

    redis_backend._run_async = fake_run_async  # type: ignore[method-assign]

    assert redis_backend.get_system("Sol") is None
    assert ("Lookup failed for system={}", ("Sol",)) in logger.messages("exception")


def test_add_neighbors_for_missing_record_logs_zero_updates(
    redis_backend: ed_redis.EDRedis,
    logger: ThreadSafeLogger,
    sample_system: dict[str, Any],
    sample_neighbors: list[dict[str, Any]],
) -> None:
    redis_backend.add_neighbors(sample_system, sample_neighbors)
    assert (
        "Updated neighbors for system={} updated_rows=0",
        ("Sol",),
    ) in logger.messages("debug")


def test_get_all_systems_returns_empty_when_store_has_no_members(
    redis_backend: ed_redis.EDRedis, logger: ThreadSafeLogger
) -> None:
    assert redis_backend.get_all_systems() == []
    assert ("Loaded all systems count=0", ()) in logger.messages("debug")


def test_import_datasource_validates_dir_and_imports_json_payloads(
    tmp_path: Path, redis_backend: ed_redis.EDRedis
) -> None:
    missing_dir = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="Import directory does not exist"):
        redis_backend.import_datasource(str(missing_dir))

    import_dir = tmp_path / "import"
    import_dir.mkdir()
    (import_dir / "systems.json").write_text(
        json.dumps(
            [
                {"name": "Sol", "id64": 1},
                {"name": "Lave", "id64": 2},
                "ignored",
            ]
        ),
        encoding="utf-8",
    )
    (import_dir / "single.json").write_text(
        json.dumps({"name": "Achenar", "id64": 3}),
        encoding="utf-8",
    )
    (import_dir / "skip.txt").write_text("ignored", encoding="utf-8")

    redis_backend.init_datasource(str(import_dir))

    assert [system["name"] for system in redis_backend.get_all_systems()] == [
        "Achenar",
        "Lave",
        "Sol",
    ]


def test_export_datasource_writes_safe_filenames_and_skips_missing_records(
    tmp_path: Path, redis_backend: ed_redis.EDRedis
) -> None:
    redis_backend.insert_system({"name": "Sol/Prime", "id64": 1})
    redis_backend.insert_system({"name": "Lave", "id64": 2})

    export_dir = tmp_path / "export"
    redis_backend.export_datasource(str(export_dir))

    sol_path = export_dir / "Sol_Prime.json"
    lave_path = export_dir / "Lave.json"

    assert sol_path.exists() is True
    assert lave_path.exists() is True
    assert json.loads(sol_path.read_text(encoding="utf-8"))["name"] == "Sol/Prime"
    assert json.loads(lave_path.read_text(encoding="utf-8"))["name"] == "Lave"


def test_export_datasource_skips_blank_names_and_lookup_misses(tmp_path: Path) -> None:
    logger = ThreadSafeLogger()
    backend = ed_redis.EDRedis("test", "redis://localhost:6379/0", logger, 1)
    export_dir = tmp_path / "export"

    backend.get_all_systems = lambda: [  # type: ignore[method-assign]
        {"name": ""},
        {"name": "Sol"},
    ]
    backend.get_system = lambda system_name: None if system_name == "Sol" else {"name": system_name}  # type: ignore[method-assign]

    backend.export_datasource(str(export_dir))

    assert list(export_dir.iterdir()) == []


def test_new_client_uses_env_max_connections_when_not_explicit(
    monkeypatch: pytest.MonkeyPatch,
    logger: ThreadSafeLogger,
    fake_redis: FakeRedisFactory,
) -> None:
    monkeypatch.setenv(redis_max_connections_env, "13")
    backend = ed_redis.EDRedis("test", "redis://localhost:6379/0", logger, None)  # type: ignore[arg-type]

    client = backend._new_client()

    assert isinstance(client, FakeRedisClient)
    assert fake_redis.calls[-1]["decode_responses"] is True
    assert fake_redis.calls[-1]["max_connections"] == 13


def test_write_lock_serializes_multithreaded_mutations(
    redis_backend: ed_redis.EDRedis,
    sample_system: dict[str, Any],
    sample_neighbors: list[dict[str, Any]],
) -> None:
    barrier = threading.Barrier(2)
    tracker_lock = threading.Lock()
    active_writes = 0
    max_active_writes = 0
    call_count = 0

    def fake_run_async(coro: Any) -> None:
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
        return None

    redis_backend._run_async = fake_run_async  # type: ignore[method-assign]

    def do_insert() -> None:
        barrier.wait()
        redis_backend.insert_system(sample_system)

    def do_add_neighbors() -> None:
        barrier.wait()
        redis_backend.add_neighbors(sample_system, sample_neighbors)

    threads = [
        threading.Thread(target=do_insert),
        threading.Thread(target=do_add_neighbors),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert call_count == 2
    assert max_active_writes == 1


def test_close_is_idempotent_and_prevents_future_operations(
    redis_backend: ed_redis.EDRedis, sample_system: dict[str, Any]
) -> None:
    redis_backend.close()
    redis_backend.close()

    with pytest.raises(RuntimeError, match="Redis client is closed"):
        redis_backend.insert_system(sample_system)

    with pytest.raises(RuntimeError, match="Redis client is closed"):
        redis_backend.get_all_systems()


def test_close_lock_is_thread_safe(redis_backend: ed_redis.EDRedis) -> None:
    threads = [threading.Thread(target=redis_backend.close) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert redis_backend._closed is True


def test_logger_collects_multithreaded_messages_without_losing_entries(
    logger: ThreadSafeLogger,
) -> None:
    barrier = threading.Barrier(4)

    def worker(index: int) -> None:
        barrier.wait()
        for offset in range(25):
            logger.debug("message {}", index * 25 + offset)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    debug_messages = logger.messages("debug")
    assert len(debug_messages) == 100
    assert len({args[0] for _, args in debug_messages}) == 100


def test_system_key_namespaces_by_datasource(redis_backend: ed_redis.EDRedis) -> None:
    assert redis_backend._system_key("Sol") == f"{default_redis_store_name}:system:Sol"
    assert redis_backend._systems_set_key == f"{default_redis_store_name}:systems"


def test_run_async_rejects_calls_after_close(redis_backend: ed_redis.EDRedis) -> None:
    redis_backend.close()

    async def returns_value() -> str:
        return value_key

    coro = returns_value()
    with pytest.raises(RuntimeError, match="Redis client is closed"):
        redis_backend._run_async(coro)
    coro.close()


def test_module_main_is_a_noop() -> None:
    assert ed_redis.main() is None
