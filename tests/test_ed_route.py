# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
from pathlib import Path
from typing import Any, cast

import pytest

import ed_route
from tests.helpers import ThreadSafeLogger


class FakeBulkLoad:
    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback,
    ) -> list[str]:
        progress_callback("loaded")
        return initial_system_names[:max_nodes_visited]


class FakePathService:
    async def run(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback,
    ) -> list[str] | None:
        progress_callback("path")
        return [initial_system_name, destination_name]


class FakeInitService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, import_dir: str | Path = "./init") -> None:
        self.calls.append(str(import_dir))


class FakeSystemInfoService:
    def run(self, system_name: str) -> dict[str, str]:
        return {"name": system_name}


class FakeSystemNamesService:
    def run(self) -> list[str]:
        return ["Sol", "Lave"]


class FakeDistanceService:
    def run(self, system_name_one: str, system_name_two: str) -> float:
        return 5.0


def build_route_service() -> ed_route.EDRouteService:
    return ed_route.EDRouteService(
        datasource=cast(Any, object()),
        cache=cast(Any, object()),
        bfs=cast(Any, object()),
        logger=ThreadSafeLogger(),
        init_datasource_service=FakeInitService(),
        get_system_info_service=FakeSystemInfoService(),
        get_all_system_names_service=FakeSystemNamesService(),
        bulk_load_cache_service=FakeBulkLoad(),
        path_service=FakePathService(),
        calc_systems_distance_service=FakeDistanceService(),
    )


def test_route_service_validates_constructor_args() -> None:
    with pytest.raises(ValueError, match="logger of type LoggingProtocol is required"):
        ed_route.EDRouteService(
            None, None, None, None, None, None, None, None, None, None
        )


@pytest.mark.asyncio
async def test_route_service_delegates_to_subservices() -> None:
    service = build_route_service()
    progress: list[str] = []

    service.init_datasource("./seed")
    assert service.get_system_info("Sol") == {"name": "Sol"}
    assert service.get_all_system_names() == ["Sol", "Lave"]
    assert service.bulk_load_cache(["Sol"], 1, progress.append) == ["Sol"]
    assert await service.path("Sol", "Lave", 10, 0, 100, progress.append) == [
        "Sol",
        "Lave",
    ]
    assert service.calc_systems_distance("Sol", "Lave") == 5.0
    assert progress == ["loaded", "path"]
