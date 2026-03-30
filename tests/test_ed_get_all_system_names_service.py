# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import threading
from pathlib import Path
import time

import pytest

import ed_get_all_system_names_service
from tests.helpers import ThreadSafeLogger


class FakeDatasource:
    def __init__(self) -> None:
        self.calls = 0

    def init_datasource(self, import_dir: str | Path = "./init") -> None:
        return None

    def get_all_systems(self) -> list[dict[str, object]]:
        self.calls += 1
        time.sleep(0.02)
        return [{"name": "Sol"}, {"name": "Lave"}, {"id64": 3}]

    def get_system(self, system_name: str) -> dict[str, object] | None:
        return None

    def insert_system(self, system_info: dict[str, object]) -> None:
        return None

    def add_neighbors(
        self, system_info: dict[str, object], new_neighbors: list[dict[str, object]]
    ) -> None:
        return None


def test_get_all_system_names_service_validates_dependencies() -> None:
    with pytest.raises(ValueError, match="logger of type LoggingProtocol is required"):
        ed_get_all_system_names_service.EDGetAllSystemNamesService(
            FakeDatasource(), None
        )

    with pytest.raises(
        ValueError, match="datasource of type DatasourceProtocol is required"
    ):
        ed_get_all_system_names_service.EDGetAllSystemNamesService(
            None, ThreadSafeLogger()
        )


def test_get_all_system_names_service_collects_names_and_logs() -> None:
    logger = ThreadSafeLogger()
    service = ed_get_all_system_names_service.EDGetAllSystemNamesService(
        FakeDatasource(), logger
    )

    assert service.run() == ["Sol", "Lave"]
    assert ("Collected {} system names", (2,)) in logger.messages("debug")


def test_get_all_system_names_service_lock_serializes_threads() -> None:
    logger = ThreadSafeLogger()
    service = ed_get_all_system_names_service.EDGetAllSystemNamesService(
        FakeDatasource(), logger
    )
    barrier = threading.Barrier(3)
    results: list[list[str]] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        value = service.run()
        with lock:
            results.append(value)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [["Sol", "Lave"]] * 3
