import threading
import time

import pytest
import test_data

from ed_redis import EDRedis


def main() -> None: ...


class _FakeRedisStore:
    def __init__(self):
        self.strings: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}


class _FakeRedisClient:
    def __init__(self, store: _FakeRedisStore):
        self._store = store
        self.closed = False

    async def exists(self, key: str) -> int:
        return 1 if key in self._store.strings else 0

    async def set(self, key: str, value: str) -> bool:
        self._store.strings[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._store.strings.get(key)

    async def sadd(self, key: str, member: str) -> int:
        members = self._store.sets.setdefault(key, set())
        size_before = len(members)
        members.add(member)
        return len(members) - size_before

    async def smembers(self, key: str) -> set[str]:
        return self._store.sets.get(key, set())

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self._store.strings.get(key) for key in keys]

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture()
def fake_redis(monkeypatch):
    import ed_redis

    store = _FakeRedisStore()
    fake_client = _FakeRedisClient(store)
    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 8)
    monkeypatch.delenv("REDIS_MAX_CONNECTIONS", raising=False)

    def _fake_from_url(
        _url: str, decode_responses: bool = False, max_connections: int | None = None
    ):
        assert decode_responses is True
        assert max_connections == 8
        return fake_client

    monkeypatch.setattr(ed_redis.redis, "from_url", _fake_from_url)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    return {"store": store, "client": fake_client}


def test_redis_crud_system(fake_redis):
    database = EDRedis("unit-test-db")

    database.insert_system(test_data.sol_data)
    database.insert_system(test_data.sol_data)
    assert database.get_system("Sol") == test_data.sol_data
    database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)
    assert database.get_system("Sol")["neighbors"] == test_data.sol_complete_neighbors


def test_redis_get_all_systems(fake_redis):
    database = EDRedis("unit-test-db")
    database.insert_system(test_data.sol_data)
    database.insert_system(test_data.wise_data)

    systems = database.get_all_systems()
    system_names = {entry["name"] for entry in systems}
    assert system_names == {"Sol", "WISE 0410+1502"}


def test_redis_get_system_when_record_not_available(fake_redis):
    database = EDRedis("unit-test-db")
    assert database.get_system("NonExistentSystem") is None


def test_redis_add_neighbors_when_record_not_available(fake_redis):
    database = EDRedis("unit-test-db")
    database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)


def test_redis_requires_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValueError, match="REDIS_URL is required"):
        EDRedis("unit-test-db")


def test_redis_write_lock_serializes_insert_and_add_neighbors(fake_redis):
    database = EDRedis("unit-test-db")
    barrier = threading.Barrier(2)
    tracker_lock = threading.Lock()
    active_writes = 0
    max_active_writes = 0
    call_count = 0

    def fake_run_async(coro):
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

    database._run_async = fake_run_async  # type: ignore[method-assign]

    def do_insert() -> None:
        barrier.wait()
        database.insert_system(test_data.sol_data)

    def do_add_neighbors() -> None:
        barrier.wait()
        database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)

    insert_thread = threading.Thread(target=do_insert)
    add_neighbors_thread = threading.Thread(target=do_add_neighbors)
    insert_thread.start()
    add_neighbors_thread.start()
    insert_thread.join()
    add_neighbors_thread.join()

    assert call_count == 2
    assert max_active_writes == 1


def test_redis_close_closes_client_and_prevents_operations(fake_redis):
    database = EDRedis("unit-test-db")
    database.close()
    with pytest.raises(RuntimeError, match="Redis client is closed"):
        database.insert_system(test_data.sol_data)


def test_redis_app_name_env_used_for_system_key(monkeypatch):
    import ed_redis

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("REDIS_APP_NAME", "myapp")
    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 4)
    monkeypatch.setattr(
        ed_redis.redis,
        "from_url",
        lambda *_args, **_kwargs: _FakeRedisClient(_FakeRedisStore()),
    )

    database = EDRedis.create()
    assert database._system_key("Sol") == "myapp:system:Sol"


def test_redis_max_connections_env_overrides_default(monkeypatch):
    import ed_redis

    captured: dict[str, int | None] = {"max_connections": None}
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "13")

    def _fake_from_url(
        _url: str, decode_responses: bool = False, max_connections: int | None = None
    ):
        assert decode_responses is True
        captured["max_connections"] = max_connections
        return _FakeRedisClient(_FakeRedisStore())

    monkeypatch.setattr(ed_redis.redis, "from_url", _fake_from_url)

    database = EDRedis("unit-test-db")
    database._new_client()

    assert captured["max_connections"] == 13


def test_redis_url_env_and_explicit_arg_precedence(monkeypatch):
    import ed_redis

    captured: dict[str, str] = {"url": ""}
    monkeypatch.setenv("REDIS_URL", "redis://env-host:6379/0")
    monkeypatch.setattr(ed_redis.psutil, "cpu_count", lambda logical=False: 2)

    def _fake_from_url(
        _url: str, decode_responses: bool = False, max_connections: int | None = None
    ):
        captured["url"] = _url
        return _FakeRedisClient(_FakeRedisStore())

    monkeypatch.setattr(ed_redis.redis, "from_url", _fake_from_url)

    database_from_env = EDRedis("unit-test-db")
    database_from_env._new_client()
    assert captured["url"] == "redis://env-host:6379/0"

    database_from_arg = EDRedis("unit-test-db", redis_url="redis://arg-host:6379/0")
    database_from_arg._new_client()
    assert captured["url"] == "redis://arg-host:6379/0"


def test_redis_init_datasource_skips_loading_when_target_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    database = EDRedis("unit-test-db")
    inserted: list[dict] = []
    database.insert_system = inserted.append  # type: ignore[method-assign]
    empty_init = tmp_path / "init"
    empty_init.mkdir(parents=True, exist_ok=True)

    database.init_datasource(str(empty_init))

    assert inserted == []


def test_redis_init_datasource_loads_records_from_init_json_files(monkeypatch, tmp_path):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    init_dir = tmp_path / "init"
    init_dir.mkdir(parents=True, exist_ok=True)
    (init_dir / "single.json").write_text(
        '{"name":"Sol","id64":1,"coords":{"x":0,"y":0,"z":0}}',
        encoding="utf-8",
    )
    (init_dir / "bulk.json").write_text(
        '[{"name":"Sirius","id64":2},{"name":"Lave","id64":3}]',
        encoding="utf-8",
    )
    (init_dir / "ignore.txt").write_text("not json", encoding="utf-8")

    database = EDRedis("unit-test-db")
    inserted: list[dict] = []
    database.insert_system = inserted.append  # type: ignore[method-assign]

    database.init_datasource(str(init_dir))

    assert {entry["name"] for entry in inserted} == {"Sol", "Sirius", "Lave"}


if __name__ == "__main__":
    main()
