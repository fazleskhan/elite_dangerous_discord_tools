import threading
import time

import pytest

import ed_get_system_info_service
from tests.helpers import ThreadSafeLogger


class FakeCache:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def find_system_info(self, system_name: str) -> dict[str, str]:
        self.calls.append(system_name)
        time.sleep(0.02)
        return {"name": system_name}


def test_get_system_info_service_validates_dependencies() -> None:
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_get_system_info_service.EDGetSystemInfoService(FakeCache(), None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="cache of type CacheProtocol is required"):
        ed_get_system_info_service.EDGetSystemInfoService(None, ThreadSafeLogger())  # type: ignore[arg-type]


def test_get_system_info_service_runs_through_cache() -> None:
    logger = ThreadSafeLogger()
    service = ed_get_system_info_service.EDGetSystemInfoService.create(
        FakeCache(), logger
    )
    assert service.run("Sol") == {"name": "Sol"}
    assert (
        "Fetching system info via service for system={}",
        ("Sol",),
    ) in logger.messages("debug")


def test_get_system_info_service_lock_allows_threaded_access() -> None:
    service = ed_get_system_info_service.EDGetSystemInfoService.create(
        FakeCache(), ThreadSafeLogger()
    )
    barrier = threading.Barrier(4)
    results: list[dict[str, str]] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        barrier.wait()
        value = service.run(f"System-{index}")
        with lock:
            results.append(value)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 4
