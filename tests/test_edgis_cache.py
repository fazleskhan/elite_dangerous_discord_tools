import pytest

import edgis_cache
from tests.helpers import ThreadSafeLogger


class FakeDatasource:
    def __init__(self) -> None:
        self.systems: dict[str, dict[str, object]] = {}
        self.added_neighbors: list[tuple[str, list[dict[str, object]]]] = []

    def get_system(self, system_name: str) -> dict[str, object] | None:
        return self.systems.get(system_name)

    def insert_system(self, system_info: dict[str, object]) -> None:
        self.systems[system_info["name"]] = dict(system_info)

    def add_neighbors(self, system_info: dict[str, object], neighbors: list[dict[str, object]]) -> None:
        entry = dict(self.systems.get(system_info["name"], system_info))
        entry["neighbors"] = neighbors
        self.systems[system_info["name"]] = entry
        self.added_neighbors.append((system_info["name"], neighbors))


def sample_system() -> dict[str, object]:
    return {"name": "Sol", "coords": {"x": 0, "y": 0, "z": 0}}


def test_edgis_cache_validates_dependencies() -> None:
    logger = ThreadSafeLogger()
    datasource = FakeDatasource()
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        edgis_cache.EDGisCache(datasource, lambda _name: None, lambda _x, _y, _z: None, logging_utils=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="datasource of type DatasourceProtocol is required"):
        edgis_cache.EDGisCache(None, lambda _name: None, lambda _x, _y, _z: None, logging_utils=logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fetch_system_info_fn of type FetchSystemInfoFn is required"):
        edgis_cache.EDGisCache(datasource, None, lambda _x, _y, _z: None, logging_utils=logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fetch_neighbors_fn of type FetchNeighborsFn is required"):
        edgis_cache.EDGisCache(datasource, lambda _name: None, None, logging_utils=logger)  # type: ignore[arg-type]


def test_edgis_cache_fetches_and_caches_system_info_and_neighbors() -> None:
    logger = ThreadSafeLogger()
    datasource = FakeDatasource()
    cache = edgis_cache.EDGisCache.create(
        datasource,
        logger,
        lambda system_name: sample_system() if system_name == "Sol" else None,
        lambda x, y, z: [{"name": "Alpha", "coords": {"x": x, "y": y, "z": z}}],
    )

    assert cache.find_system_info("Sol") == sample_system()
    assert cache.find_system_info("Sol") == sample_system()
    assert cache.find_system_neighbors(sample_system()) == [{"name": "Alpha", "coords": {"x": 0, "y": 0, "z": 0}}]
    assert cache.find_system_neighbors(sample_system()) == [{"name": "Alpha", "coords": {"x": 0, "y": 0, "z": 0}}]
    assert datasource.added_neighbors == [("Sol", [{"name": "Alpha", "coords": {"x": 0, "y": 0, "z": 0}}])]


def test_edgis_cache_logs_failures() -> None:
    logger = ThreadSafeLogger()
    cache = edgis_cache.EDGisCache.create(
        FakeDatasource(),
        logger,
        lambda _system_name: None,
        lambda _x, _y, _z: None,
    )

    assert cache.find_system_info("Missing") is None
    assert cache.find_system_neighbors(sample_system()) is None
    assert logger.messages("warning")


def test_edgis_cache_main_is_a_noop() -> None:
    assert edgis_cache.main() is None
