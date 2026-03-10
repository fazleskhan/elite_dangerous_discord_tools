import time

import pytest

import ed_bfs_algo
from tests.helpers import ThreadSafeLogger


def test_bfs_validates_dependencies() -> None:
    logger = ThreadSafeLogger()
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_bfs_algo.EDBfsAlgo(lambda _name: None, lambda _info: None, lambda _a, _b: 0.0, None)  # type: ignore[arg-type]
    with pytest.raises(
        ValueError, match="fetch_info_fn of type FetchSystemInfoFn is required"
    ):
        ed_bfs_algo.EDBfsAlgo(None, lambda _info: None, lambda _a, _b: 0.0, logger)  # type: ignore[arg-type]
    with pytest.raises(
        ValueError, match="fetch_info_fn of type FetchSystemInfoFn is required"
    ):
        ed_bfs_algo.EDBfsAlgo(lambda _name: None, None, lambda _a, _b: 0.0, logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="distance_fn of type DistanceFn is required"):
        ed_bfs_algo.EDBfsAlgo(lambda _name: None, lambda _info: None, None, logger)  # type: ignore[arg-type]


def test_bfs_reconstruct_path_and_same_start() -> None:
    assert ed_bfs_algo.EDBfsAlgo._reconstruct_path({"B": "A", "A": None}, "B") == [
        "A",
        "B",
    ]
    bfs = ed_bfs_algo.EDBfsAlgo.create(
        lambda name: {"name": name},
        lambda _info: [],
        lambda _one, _two: 0.0,
        ThreadSafeLogger(),
    )
    assert bfs.travel("Sol", "Sol", 10, 0, 100, lambda _message: None) == ["Sol"]


def test_bfs_travel_finds_path_and_filters_edges() -> None:
    graph = {
        "A": [{"name": "B", "distance": 1}, {"name": "C", "distance": 3}],
        "B": [{"name": "T", "distance": 8}],
        "C": [{"name": "T", "distance": 4}],
        "T": [],
    }
    heuristic = {"A": 10, "B": 9, "C": 4, "T": 0}
    bfs = ed_bfs_algo.EDBfsAlgo.create(
        lambda name: {"name": name},
        lambda info: graph[info["name"]],
        lambda one, _two: heuristic[one],
        ThreadSafeLogger(),
    )

    assert bfs.travel("A", "T", 10, 2, 5, lambda _message: None) == ["A", "C", "T"]


def test_bfs_reports_progress_and_missing_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = ThreadSafeLogger()
    progress: list[str] = []
    graph = {"A": [{"name": f"N{index}", "distance": 3} for index in range(1, 512)]}
    graph.update({f"N{index}": [] for index in range(1, 512)})
    # Force the 512-node progress branch without waiting for real wall-clock time.
    monotonic_values = iter([0.0, 31.0, 62.0])
    monkeypatch.setattr(ed_bfs_algo.time, "monotonic", lambda: next(monotonic_values))
    bfs = ed_bfs_algo.EDBfsAlgo.create(
        lambda name: None if name == "N1" else {"name": name},
        lambda info: graph.get(info["name"], []),
        lambda _one, _two: 1.0,
        logger,
    )

    assert bfs.travel("A", "Missing", 600, 0, 10, progress.append) is None
    assert progress == ["Analyzed 512 of 600 systems"]
    assert ("Skipping node with missing system info: {}", ("N1",)) in logger.messages(
        "debug"
    )


def test_bfs_respects_max_count() -> None:
    bfs = ed_bfs_algo.EDBfsAlgo.create(
        lambda name: {"name": name},
        lambda _info: [{"name": "B", "distance": 1}],
        lambda _one, _two: 0.0,
        ThreadSafeLogger(),
    )
    # `max_count=0` trips the guard before the first expansion.
    assert bfs.travel("A", "T", 0, 0, 10, lambda _message: None) is None


def test_bfs_main_is_a_noop() -> None:
    assert ed_bfs_algo.main() is None
