from __future__ import annotations

import asyncio
import math
import threading
from typing import Any, Callable, Protocol

from loguru import logger

import ed_bfs
import ed_cache
from ed_bfs import EDBfs
from ed_cache import EDBulkLoad
from ed_constants import (
    default_init_dir,
    system_info_coords_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)
from ed_route_services import (
    EDBulkLoadCacheService,
    EDCalcSystemsDistanceService,
    EDGetAllSystemNamesService,
    EDGetSystemInfoService,
    EDInitDatasourceService,
    EDPathService,
)

"""Service layer that composes datasource/cache dependencies and route search."""

SystemInfo = dict[str, Any]
ProgressFn = Callable[[str], None]


class DBProtocol(Protocol):
    def init_datasource(self, import_dir: str = default_init_dir) -> None: ...
    def get_all_systems(self) -> list[SystemInfo]: ...


class CacheProtocol(Protocol):
    def find_system_info(self, system_name: str) -> SystemInfo | None: ...
    def find_system_neighbors(
        self, system_info: SystemInfo
    ) -> list[SystemInfo] | None: ...
    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float: ...


def main() -> None: ...


class EDRouteService:
    """Thin shim layer over delegate service classes."""

    def __init__(
        self,
        db_path: str,
        database: DBProtocol | None,
        cache: CacheProtocol | None,
        travel_fn: Callable[..., list[str] | None] | None,
        script_file: str,
        *,
        init_datasource_service: EDInitDatasourceService | None = None,
        get_system_info_service: EDGetSystemInfoService | None = None,
        get_all_system_names_service: EDGetAllSystemNamesService | None = None,
        bulk_load_cache_service: EDBulkLoadCacheService | None = None,
        path_service: EDPathService | None = None,
        calc_systems_distance_service: EDCalcSystemsDistanceService | None = None,
        logging_utils: Any = None,
    ) -> None:
        self.db_path = db_path
        self.database = database
        self.cache = cache
        self.travel_fn = travel_fn
        self.script_file = script_file
        self.logger = logger
        self.logging_utils = logging_utils
        self._coords_cache: dict[str, tuple[float, float, float]] = {}
        self._coords_cache_lock = threading.Lock()

        self._init_datasource_service = init_datasource_service
        self._get_system_info_service = get_system_info_service
        self._get_all_system_names_service = get_all_system_names_service
        self._bulk_load_cache_service = bulk_load_cache_service
        self._path_service = path_service
        self._calc_systems_distance_service = calc_systems_distance_service

        if self._init_datasource_service is None and self.database is not None:
            self._init_datasource_service = EDInitDatasourceService.create(
                self.database, self.logging_utils
            )
        if self._get_system_info_service is None and self.cache is not None:
            self._get_system_info_service = EDGetSystemInfoService.create(
                self.cache, self.logging_utils
            )
        if self._get_all_system_names_service is None and self.database is not None:
            self._get_all_system_names_service = EDGetAllSystemNamesService.create(
                self.database, self.logging_utils
            )
        if self._calc_systems_distance_service is None and self._get_system_info_service is not None:
            self._calc_systems_distance_service = EDCalcSystemsDistanceService.create(
                self._get_system_info_service,
                self.logging_utils,
            )
        if self._path_service is None and self.cache is not None:
            bfs = EDBfs.create(self.cache, self.logging_utils)
            if self._calc_systems_distance_service is None:
                self._calc_systems_distance_service = EDCalcSystemsDistanceService.create(
                    EDGetSystemInfoService.create(self.cache, self.logging_utils),
                    self.logging_utils,
                )
            self._path_service = EDPathService.create(
                bfs,
                self._calc_systems_distance_service,
                self.logging_utils,
            )
        if self._bulk_load_cache_service is None and self.cache is not None:
            bulk_load = EDBulkLoad.create(self.cache, self.logging_utils)
            self._bulk_load_cache_service = EDBulkLoadCacheService.create(
                bulk_load,
                self.logging_utils,
            )

    @staticmethod
    def create(
        datasource: DBProtocol | None = None,
        cache: CacheProtocol | None = None,
        travel_fn: Callable[..., list[str] | None] = ed_bfs.travel,
        script_file: str = __file__,
        *,
        init_datasource_service: EDInitDatasourceService | None = None,
        get_system_info_service: EDGetSystemInfoService | None = None,
        get_all_system_names_service: EDGetAllSystemNamesService | None = None,
        bulk_load_cache_service: EDBulkLoadCacheService | None = None,
        path_service: EDPathService | None = None,
        calc_systems_distance_service: EDCalcSystemsDistanceService | None = None,
        logging_utils: Any = None,
    ) -> "EDRouteService":
        # New IoC create signature (delegate services) takes precedence.
        if (
            init_datasource_service is not None
            or get_system_info_service is not None
            or get_all_system_names_service is not None
            or bulk_load_cache_service is not None
            or path_service is not None
            or calc_systems_distance_service is not None
        ):
            logger.debug("Creating EDRouteService via delegate service composition")
            return EDRouteService(
                db_path="ioc-route-service",
                database=None,
                cache=None,
                travel_fn=None,
                script_file=script_file,
                init_datasource_service=init_datasource_service,
                get_system_info_service=get_system_info_service,
                get_all_system_names_service=get_all_system_names_service,
                bulk_load_cache_service=bulk_load_cache_service,
                path_service=path_service,
                calc_systems_distance_service=calc_systems_distance_service,
                logging_utils=logging_utils,
            )

        # Backward-compatible create signature used by existing code/tests.
        if datasource is None or cache is None:
            raise ValueError("datasource and cache are required for legacy create()")
        logger.debug("Creating EDRouteService via datasource/cache composition")
        return EDRouteService(
            db_path="injected-datasource",
            database=datasource,
            cache=cache,
            travel_fn=travel_fn,
            script_file=script_file,
            logging_utils=logging_utils,
        )

    def init_datasource(self, import_dir: str = default_init_dir) -> None:
        if self._init_datasource_service is None:
            self.logger.warning("Init datasource service is not configured")
            return
        self.logger.info("Initializing datasource from {}", import_dir)
        self._init_datasource_service.run(import_dir)

    def get_system_info(self, system_name: str) -> SystemInfo | None:
        if self._get_system_info_service is None:
            self.logger.warning("Get system info service is not configured")
            return None
        self.logger.debug("Fetching system info via service for system={}", system_name)
        return self._get_system_info_service.run(system_name)

    def get_all_system_names(self) -> list[str]:
        if self._get_all_system_names_service is None:
            self.logger.warning("Get all system names service is not configured")
            return []
        results = self._get_all_system_names_service.run()
        self.logger.debug("Collected {} system names", len(results))
        return results

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        if self._bulk_load_cache_service is None:
            self.logger.warning("Bulk load cache service is not configured")
            return []
        self.logger.info(
            "Bulk loading cache from seeds={} max_nodes_visited={}",
            initial_system_names,
            max_nodes_visited,
        )
        return self._bulk_load_cache_service.run(
            initial_system_names,
            max_nodes_visited,
            progress_callback,
        )

    async def path(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        # Preserve legacy behavior when a custom travel function was injected.
        if self.travel_fn is not None and self.cache is not None:
            cache = self.cache
            loop = asyncio.get_running_loop()
            result: asyncio.Future[list[str] | None] = loop.create_future()

            def _worker() -> None:
                try:
                    route_result = self.travel_fn(
                        cache.find_system_info,
                        cache.find_system_neighbors,
                        initial_system_name,
                        destination_name,
                        max_systems,
                        min_distance,
                        max_distance,
                        self.calc_systems_distance,
                        progress_callback,
                    )
                    loop.call_soon_threadsafe(result.set_result, route_result)
                except Exception as exc:
                    loop.call_soon_threadsafe(result.set_exception, exc)

            threading.Thread(target=_worker, daemon=True).start()
            route = await result
            self.logger.info("Path calculation complete found={}", route is not None)
            return route

        if self._path_service is None:
            self.logger.warning("Path service is not configured")
            return None
        route = await self._path_service.run(
            initial_system_name,
            destination_name,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )
        self.logger.info("Path calculation complete found={}", route is not None)
        return route

    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float:
        # Keep this local implementation so tests monkeypatching `get_system_info`
        # continue to work and to preserve deterministic compatibility.
        self.logger.debug(
            "Calculating distance between systems: {} and {}",
            system_name_one,
            system_name_two,
        )
        coords_one = self._get_system_coords(system_name_one)
        coords_two = self._get_system_coords(system_name_two)
        if coords_one is None or coords_two is None:
            missing_systems: list[str] = []
            if coords_one is None:
                missing_systems.append(system_name_one)
            if coords_two is None:
                missing_systems.append(system_name_two)
            message = f"Could not load system info for: {', '.join(missing_systems)}"
            self.logger.error(message)
            raise ValueError(message)

        distance = math.sqrt(
            (coords_two[0] - coords_one[0]) ** 2
            + (coords_two[1] - coords_one[1]) ** 2
            + (coords_two[2] - coords_one[2]) ** 2
        )
        self.logger.debug(
            "Distance calculated for {} -> {}: {}",
            system_name_one,
            system_name_two,
            distance,
        )
        return distance

    def _get_system_coords(self, system_name: str) -> tuple[float, float, float] | None:
        with self._coords_cache_lock:
            cached_coords = self._coords_cache.get(system_name)
        if cached_coords is not None:
            return cached_coords

        system_info = self.get_system_info(system_name)
        if system_info is None:
            return None

        coords = system_info[system_info_coords_field]
        resolved_coords = (
            float(coords[system_info_x_field]),
            float(coords[system_info_y_field]),
            float(coords[system_info_z_field]),
        )
        with self._coords_cache_lock:
            self._coords_cache[system_name] = resolved_coords
        return resolved_coords


# Compatibility helpers retained from earlier ed_route refactors.
def create_bulk_loader(
    datasource_name: str | None = None,
    datasource_type: str | None = None,
) -> ed_cache.EDBulkLoad:
    return ed_cache.create_bulk_loader(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )


def bulk_load(
    initial_system_names: list[str],
    max_nodes_visited: int,
    progress_callback: ProgressFn | None = None,
) -> list[str]:
    return ed_cache.bulk_load(initial_system_names, max_nodes_visited, progress_callback)


async def bulk_load_async(
    initial_system_names: list[str],
    max_nodes_visited: int,
    progress_callback: ProgressFn | None = None,
) -> list[str]:
    return await ed_cache.bulk_load_async(
        initial_system_names,
        max_nodes_visited,
        progress_callback,
    )


if __name__ == "__main__":
    main()
