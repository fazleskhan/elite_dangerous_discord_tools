import ed_bulk_load_algo
import ed_datasource_factory
import edgis_cache
from ed_logging_utils import EDLoggingUtils


def main(): ...


def test_bulk_load_service_walks_neighbors_until_max_nodes():
    graph = {
        "Sol": ["Alpha Centauri", "Barnard_s Star"],
        "Alpha Centauri": ["Luyten_s Star", "Procyon"],
        "Barnard_s Star": ["Wolf 359"],
        "Luyten_s Star": [],
        "Procyon": [],
        "Wolf 359": [],
    }

    def fake_find_system_info(system_name: str):
        return {"name": system_name}

    def fake_find_neighbors(system_info):
        return [{"name": name} for name in graph[system_info["name"]]]

    bulk_loader = ed_bulk_load_algo.EDBulkLoadAlgo(
        fetch_system_info_fn=fake_find_system_info,
        fetch_neighbors_fn=fake_find_neighbors,
        logging_utils=EDLoggingUtils(),
    )
    visited = bulk_loader.load(["Sol"], 4, lambda _message: None)
    assert visited == ["Sol", "Alpha Centauri", "Barnard_s Star", "Luyten_s Star"]


def test_bulk_load_service_reuses_neighbor_payload_without_refetch():
    graph = {
        "Sol": ["Alpha Centauri"],
        "Alpha Centauri": ["Barnard_s Star"],
        "Barnard_s Star": [],
    }
    fetch_info_calls: list[str] = []

    def fake_find_system_info(system_name: str):
        fetch_info_calls.append(system_name)
        return {
            "name": system_name,
            "coords": {"x": 1.0, "y": 2.0, "z": 3.0},
        }

    def fake_find_neighbors(system_info):
        return [
            {
                "name": name,
                "coords": {"x": 1.0, "y": 2.0, "z": 3.0},
            }
            for name in graph[system_info["name"]]
        ]

    bulk_loader = ed_bulk_load_algo.EDBulkLoadAlgo(
        fetch_system_info_fn=fake_find_system_info,
        fetch_neighbors_fn=fake_find_neighbors,
        logging_utils=EDLoggingUtils(),
    )

    visited = bulk_loader.load(["Sol"], 3, lambda _message: None)

    assert visited == ["Sol", "Alpha Centauri", "Barnard_s Star"]
    # Only the initial seed needs direct info lookup; neighbors were reused.
    assert fetch_info_calls == ["Sol"]


def test_create_bulk_load_composes_datasource_and_cache():
    class FakeCache:
        def find_system_info(self, system_name):
            return {"name": system_name}

        def find_system_neighbors(self, system_info):
            return []

    cache_obj = FakeCache()
    bulk_loader = ed_bulk_load_algo.EDBulkLoadAlgo.create(
        cache=cache_obj,
        logging_utils=EDLoggingUtils(),
    )

    assert isinstance(bulk_loader, ed_bulk_load_algo.EDBulkLoadAlgo)
    assert bulk_loader.fetch_system_info_fn("Sol") == {"name": "Sol"}
    assert bulk_loader.fetch_neighbors_fn({"name": "Sol"}) == []


def test_create_bulk_loader_delegates_to_loader(monkeypatch):
    datasource_obj = object()
    cache_obj = object()
    create_calls: list[tuple[object, object]] = []

    class FakeLoader:
        def load(self, initial_system_names, max_nodes_visited, progress_callback):
            assert initial_system_names == ["Sol"]
            assert max_nodes_visited == 1
            progress_callback("ok")
            return ["Sol"]

    monkeypatch.setattr(
        ed_datasource_factory,
        "create_datasource",
        lambda datasource_name=None, datasource_type=None: datasource_obj,
    )
    monkeypatch.setattr(
        edgis_cache.EDGisCache,
        "create",
        lambda db_obj, *, logging_utils: cache_obj,
    )
    monkeypatch.setattr(
        ed_bulk_load_algo.EDBulkLoadAlgo,
        "create",
        staticmethod(
            lambda cache, logging_utils: (
                create_calls.append((cache, logging_utils)) or FakeLoader()
            )
        ),
    )

    datasource = ed_datasource_factory.create_datasource()
    cache = edgis_cache.EDGisCache.create(
        datasource,
        logging_utils=EDLoggingUtils(),
    )
    bulk_loader = ed_bulk_load_algo.EDBulkLoadAlgo.create(
        cache, logging_utils=EDLoggingUtils()
    )
    assert bulk_loader.load(["Sol"], 1, lambda _message: None) == ["Sol"]
    assert len(create_calls) == 1
    assert create_calls[0][0] is cache_obj
    assert isinstance(create_calls[0][1], EDLoggingUtils)


def test_bulk_load_service_uses_worker_pool_sized_to_physical_cores(monkeypatch):
    graph = {
        "Sol": ["Alpha Centauri", "Barnard_s Star"],
        "Alpha Centauri": [],
        "Barnard_s Star": [],
    }
    seen: dict[str, object] = {"max_workers": None, "batches": []}

    class FakeExecutor:
        def __init__(self, max_workers):
            seen["max_workers"] = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, iterable):
            batch = list(iterable)
            seen["batches"].append([item["name"] for item in batch])
            return [fn(item) for item in batch]

    def fake_find_system_info(system_name: str):
        return {"name": system_name}

    def fake_find_neighbors(system_info):
        return [{"name": name} for name in graph[system_info["name"]]]

    monkeypatch.setattr(
        ed_bulk_load_algo.EDBulkLoadAlgo,
        "_physical_core_count",
        staticmethod(lambda: 3),
    )
    monkeypatch.setattr(ed_bulk_load_algo, "ThreadPoolExecutor", FakeExecutor)

    bulk_loader = ed_bulk_load_algo.EDBulkLoadAlgo(
        fetch_system_info_fn=fake_find_system_info,
        fetch_neighbors_fn=fake_find_neighbors,
        logging_utils=EDLoggingUtils(),
    )
    visited = bulk_loader.load(["Sol"], 3, lambda _message: None)

    assert visited == ["Sol", "Alpha Centauri", "Barnard_s Star"]
    assert seen["max_workers"] == 3
    assert seen["batches"] == [["Sol"]]


if __name__ == "__main__":
    main()
