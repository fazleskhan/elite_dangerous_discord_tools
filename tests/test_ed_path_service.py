import asyncio
import threading

import pytest

import ed_path_service
from tests.helpers import ThreadSafeLogger


class FakeBfs:
    def __init__(self) -> None:
        self.thread_ids: list[int] = []

    def travel(self, initial, destination, max_systems, min_distance, max_distance, progress_callback):  # type: ignore[no-untyped-def]
        self.thread_ids.append(threading.get_ident())
        progress_callback("step")
        return [initial, destination]


class FakeDistanceService:
    def run(self, one: str, two: str) -> float:
        return 1.0


def test_path_service_validates_dependencies() -> None:
    logger = ThreadSafeLogger()
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        ed_path_service.EDPathService(FakeBfs(), FakeDistanceService(), None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bfs of type BfsProtocol is required"):
        ed_path_service.EDPathService(None, FakeDistanceService(), logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="calc_distance_service of type CalcSystemsDistanceProtocol is required"):
        ed_path_service.EDPathService(FakeBfs(), None, logger)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_path_service_runs_bfs_in_worker_thread() -> None:
    logger = ThreadSafeLogger()
    bfs = FakeBfs()
    service = ed_path_service.EDPathService.create(bfs, FakeDistanceService(), logger)
    progress: list[str] = []

    route = await service.run("Sol", "Lave", 10, 0, 100, progress.append)

    assert route == ["Sol", "Lave"]
    assert progress == ["step"]
    assert bfs.thread_ids and bfs.thread_ids[0] != threading.get_ident()
    assert ("Path calculation complete found={}", (True,)) in logger.messages("info")
