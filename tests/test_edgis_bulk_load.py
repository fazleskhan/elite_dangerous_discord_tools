import ed_cache
import edgis_bulk_load


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

    bulk_loader = ed_cache.BulkLoadService(
        fetch_system_info_fn=fake_find_system_info,
        fetch_neighbors_fn=fake_find_neighbors,
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

    bulk_loader = ed_cache.BulkLoadService(
        fetch_system_info_fn=fake_find_system_info,
        fetch_neighbors_fn=fake_find_neighbors,
    )

    visited = bulk_loader.load(["Sol"], 3, lambda _message: None)

    assert visited == ["Sol", "Alpha Centauri", "Barnard_s Star"]
    # Only the initial seed needs direct info lookup; neighbors were reused.
    assert fetch_info_calls == ["Sol"]


def test_create_bulk_loader_composes_datasource_and_cache(monkeypatch):
    datasource_obj = object()

    class FakeCache:
        def find_system_info(self, system_name):
            return {"name": system_name}

        def find_system_neighbors(self, system_info):
            return []

    cache_obj = FakeCache()

    datasource_calls: list[tuple[str, str]] = []
    cache_calls: list[object] = []

    def fake_create_datasource(datasource_name: str, datasource_type: str):
        datasource_calls.append((datasource_name, datasource_type))
        return datasource_obj

    def fake_create_cache(db_obj):
        cache_calls.append(db_obj)
        return cache_obj

    monkeypatch.setattr(ed_cache.ed_factory, "create_datasource", fake_create_datasource)
    monkeypatch.setattr(ed_cache.edgis_cache.EDGisCache, "create", fake_create_cache)

    bulk_loader = ed_cache.create_bulk_loader(
        datasource_name="test.db",
        datasource_type="tinydb",
    )

    assert isinstance(bulk_loader, ed_cache.BulkLoadService)
    assert datasource_calls == [("test.db", "tinydb")]
    assert cache_calls == [datasource_obj]


def test_edgis_bulk_load_logic_delegates_to_ed_cache(monkeypatch):
    monkeypatch.setattr(
        edgis_bulk_load.ed_cache,
        "bulk_load",
        lambda initial_system_names, max_nodes_visited: ["Sol"],
    )
    assert edgis_bulk_load.logic(["Sol"], 1) == ["Sol"]


if __name__ == "__main__":
    main()
