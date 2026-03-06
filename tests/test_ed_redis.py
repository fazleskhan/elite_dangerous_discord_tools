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
        self.hashes: dict[str, dict[str, str]] = {}
        self.counters: dict[str, int] = {}


class _FakeRedisClient:
    def __init__(self, store: _FakeRedisStore):
        self._store = store

    async def exists(self, key: str) -> int:
        return 1 if key in self._store.strings else 0

    async def incr(self, key: str) -> int:
        next_value = self._store.counters.get(key, 0) + 1
        self._store.counters[key] = next_value
        return next_value

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

    async def hset(self, key: str, field: str, value: int) -> int:
        hash_obj = self._store.hashes.setdefault(key, {})
        is_new = field not in hash_obj
        hash_obj[field] = str(value)
        return 1 if is_new else 0

    async def hget(self, key: str, field: str) -> str | None:
        hash_obj = self._store.hashes.get(key, {})
        return hash_obj.get(field)

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def fake_redis(monkeypatch):
    import ed_redis

    store = _FakeRedisStore()

    def _fake_from_url(_url: str, decode_responses: bool = False):
        assert decode_responses is True
        return _FakeRedisClient(store)

    monkeypatch.setattr(ed_redis.redis, "from_url", _fake_from_url)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    return store


def test_redis_crud_system(fake_redis):
    database = EDRedis("unit-test-db")

    assert database.insert_system(test_data.sol_data) == 1
    assert database.insert_system(test_data.sol_data) is None
    assert database.get_system("Sol") == test_data.sol_data
    assert database.add_neighbors(
        test_data.sol_data, test_data.sol_complete_neighbors
    ) == [1]
    assert database.get_system("Sol")["neighbors"] == test_data.sol_complete_neighbors


def test_redis_get_all_systems(fake_redis):
    database = EDRedis("unit-test-db")
    assert database.insert_system(test_data.sol_data) == 1
    assert database.insert_system(test_data.wise_data) == 2

    systems = database.get_all_systems()
    system_names = {entry["name"] for entry in systems}
    assert system_names == {"Sol", "WISE 0410+1502"}


def test_redis_get_system_when_record_not_available(fake_redis):
    database = EDRedis("unit-test-db")
    assert database.get_system("NonExistentSystem") is None


def test_redis_add_neighbors_when_record_not_available(fake_redis):
    database = EDRedis("unit-test-db")
    assert (
        database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)
        == []
    )


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


if __name__ == "__main__":
    main()
