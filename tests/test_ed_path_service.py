# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import threading

import pytest

import ed_path_service
from tests.helpers import ThreadSafeLogger


class FakeBfs:
    def __init__(self) -> None:
        self.thread_ids: list[int] = []

    def travel(
        self,
        start_name: str,
        destination_name: str,
        max_count: int,
        min_distance: int,
        max_distance: int,
        progress_callback,
    ) -> list[str]:
        self.thread_ids.append(threading.get_ident())
        progress_callback("step")
        return [start_name, destination_name]


class FakeDistanceService:
    def run(self, system_name_one: str, system_name_two: str) -> float:
        return 1.0


def test_path_service_validates_dependencies() -> None:
    logger = ThreadSafeLogger()
    with pytest.raises(ValueError, match="logger of type LoggingProtocol is required"):
        ed_path_service.EDPathService(FakeBfs(), FakeDistanceService(), None)
    with pytest.raises(ValueError, match="bfs of type BfsProtocol is required"):
        ed_path_service.EDPathService(None, FakeDistanceService(), logger)
    with pytest.raises(
        ValueError,
        match="calc_distance_service of type CalcSystemsDistanceProtocol is required",
    ):
        ed_path_service.EDPathService(FakeBfs(), None, logger)


@pytest.mark.asyncio
async def test_path_service_runs_bfs_in_worker_thread() -> None:
    logger = ThreadSafeLogger()
    bfs = FakeBfs()
    service = ed_path_service.EDPathService(bfs, FakeDistanceService(), logger)
    progress: list[str] = []

    route = await service.run("Sol", "Lave", 10, 0, 100, progress.append)

    assert route == ["Sol", "Lave"]
    assert progress == ["step"]
    assert bfs.thread_ids and bfs.thread_ids[0] != threading.get_ident()
    assert ("Path calculation complete found={}", (True,)) in logger.messages("info")
