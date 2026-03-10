import threading
import time

import pytest

import ed_init_datasource_service
from tests.helpers import ThreadSafeLogger


class FakeDatasource:
    def __init__(self) -> None:
        self.import_dirs: list[str] = []

    def init_datasource(self, import_dir: str = "./init") -> None:
        time.sleep(0.02)
        self.import_dirs.append(import_dir)


def test_init_datasource_service_validates_dependencies() -> None:
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_init_datasource_service.EDInitDatasourceService(FakeDatasource(), None)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError, match="datasource of type DatasourceProtocol is required"
    ):
        ed_init_datasource_service.EDInitDatasourceService(None, ThreadSafeLogger())  # type: ignore[arg-type]


def test_init_datasource_service_runs_and_logs() -> None:
    logger = ThreadSafeLogger()
    datasource = FakeDatasource()
    service = ed_init_datasource_service.EDInitDatasourceService.create(
        datasource, logger
    )
    service.run("./seed")

    assert datasource.import_dirs == ["./seed"]
    assert ("Initializing datasource from {}", ("./seed",)) in logger.messages("info")


def test_init_datasource_service_lock_handles_threads() -> None:
    datasource = FakeDatasource()
    service = ed_init_datasource_service.EDInitDatasourceService.create(
        datasource, ThreadSafeLogger()
    )
    barrier = threading.Barrier(3)

    def worker(index: int) -> None:
        barrier.wait()
        service.run(f"./seed-{index}")

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(datasource.import_dirs) == ["./seed-0", "./seed-1", "./seed-2"]
