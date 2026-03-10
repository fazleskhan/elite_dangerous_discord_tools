import threading

import pytest

import ed_bulk_load_algo
from tests.helpers import ThreadSafeLogger


class FakeCache:
    def find_system_info(self, system_name: str) -> dict[str, object]:
        return {"name": system_name}

    def find_system_neighbors(self, system_info: dict[str, object]) -> list[dict[str, object]]:
        return [{"name": f"{system_info['name']}-N"}]


def test_bulk_load_algo_validates_dependencies() -> None:
    logger = ThreadSafeLogger()
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        ed_bulk_load_algo.EDBulkLoadAlgo(lambda _name: None, lambda _info: None, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fetch_system_info_fn of type FetchInfoFn is required"):
        ed_bulk_load_algo.EDBulkLoadAlgo(None, lambda _info: None, logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fetch_neighbors_fn of type FetchNeighborsFn is required"):
        ed_bulk_load_algo.EDBulkLoadAlgo(lambda _name: None, None, logger)  # type: ignore[arg-type]


def test_bulk_load_algo_create_and_neighbor_payload_handling() -> None:
    algo = ed_bulk_load_algo.EDBulkLoadAlgo.create(FakeCache(), ThreadSafeLogger())
    assert algo.fetch_system_info_fn("Sol") == {"name": "Sol"}
    assert algo._neighbor_as_system_info({"name": "Sol"}) is None
    assert algo._neighbor_as_system_info({"name": "Sol", "coords": {"x": 1, "y": 2, "z": 3}}) == {
        "name": "Sol",
        "coords": {"x": 1, "y": 2, "z": 3},
    }


def test_bulk_load_algo_loads_neighbors_and_respects_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = {
        "Sol": [{"name": "Alpha", "coords": {"x": 1, "y": 2, "z": 3}}, {"name": "Beta"}],
        "Alpha": [{"name": "Gamma", "coords": {"x": 1, "y": 2, "z": 3}}],
        "Beta": [],
        "Gamma": [],
    }
    fetched_info: list[str] = []
    progress: list[str] = []

    class FakeExecutor:
        def __init__(self, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> "FakeExecutor":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def map(self, fn, iterable):  # type: ignore[no-untyped-def]
            return [fn(item) for item in iterable]

    monkeypatch.setattr(ed_bulk_load_algo, "ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(ed_bulk_load_algo.EDBulkLoadAlgo, "_physical_core_count", staticmethod(lambda: 2))

    algo = ed_bulk_load_algo.EDBulkLoadAlgo(
        lambda name: fetched_info.append(name) or {"name": name, "coords": {"x": 0, "y": 0, "z": 0}},
        lambda info: graph[info["name"]],
        ThreadSafeLogger(),
    )
    assert algo.load(["Sol", "Sol", " "], 3, progress.append) == ["Sol", "Alpha", "Beta"]
    assert fetched_info == ["Sol", "Beta"]
    assert progress == []


def test_bulk_load_algo_handles_zero_limit_and_threaded_fetch() -> None:
    logger = ThreadSafeLogger()
    algo = ed_bulk_load_algo.EDBulkLoadAlgo(
        lambda name: {"name": name},
        lambda info: [],
        logger,
    )
    assert algo.load(["Sol"], 0, lambda _message: None) == []
    assert ("Skipping bulk load due to non-positive max_nodes_visited={}", (0,)) in logger.messages("warning")


def test_bulk_load_algo_physical_core_count_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ed_bulk_load_algo.psutil, "cpu_count", lambda logical=False: None if not logical else 8)
    assert ed_bulk_load_algo.EDBulkLoadAlgo._physical_core_count() == 8


def test_bulk_load_algo_fetch_neighbors_logs_system_name() -> None:
    logger = ThreadSafeLogger()
    algo = ed_bulk_load_algo.EDBulkLoadAlgo(
        lambda name: {"name": name},
        lambda _info: [{"name": "Next"}],
        logger,
    )
    assert algo._fetch_neighbors({"name": "Sol"}) == [{"name": "Next"}]
    assert ("Fetching neighbors for system={}", ("Sol",)) in logger.messages("debug")


def test_bulk_load_algo_main_is_a_noop() -> None:
    assert ed_bulk_load_algo.main() is None
