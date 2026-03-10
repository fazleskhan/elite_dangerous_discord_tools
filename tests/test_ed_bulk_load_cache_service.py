import pytest

import ed_bulk_load_cache_service
from tests.helpers import ThreadSafeLogger


class FakeBulkLoad:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int]] = []

    def load(self, initial_system_names: list[str], max_nodes_visited: int, progress_callback):  # type: ignore[no-untyped-def]
        self.calls.append((initial_system_names, max_nodes_visited))
        progress_callback("loaded")
        return initial_system_names[:max_nodes_visited]


def test_bulk_load_cache_service_validates_dependencies() -> None:
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_bulk_load_cache_service.EDBulkLoadCacheService(FakeBulkLoad(), None)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError, match="bulk_load of type BulkLoadProtocol is required"
    ):
        ed_bulk_load_cache_service.EDBulkLoadCacheService(None, ThreadSafeLogger())  # type: ignore[arg-type]


def test_bulk_load_cache_service_delegates_and_logs() -> None:
    logger = ThreadSafeLogger()
    bulk_load = FakeBulkLoad()
    service = ed_bulk_load_cache_service.EDBulkLoadCacheService.create(
        bulk_load, logger
    )
    progress: list[str] = []

    assert service.load(["Sol", "Lave"], 1, progress.append) == ["Sol"]
    assert bulk_load.calls == [(["Sol", "Lave"], 1)]
    assert progress == ["loaded"]
    assert (
        "Bulk loading cache from seeds={} max_nodes_visited={}",
        (["Sol", "Lave"], 1),
    ) in logger.messages("info")
