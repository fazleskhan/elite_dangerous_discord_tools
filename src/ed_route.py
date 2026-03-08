import edgis_cache
import datasource
import ed_bfs
import constants
import os
import asyncio
import threading
from concurrent.futures import Future
from loguru import logger
from dotenv import load_dotenv
from typing import Any, Callable, Protocol, cast
import math

"""Service layer that composes DB/cache dependencies and route search."""


SystemInfo = dict[str, Any]
ProgressFn = Callable[[str], None]


class DBProtocol(Protocol):
    def init_datasource(self, import_dir: str = "./init") -> None: ...
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
    """Routing service with injected dependencies for easier testing."""

    def __init__(
        self,
        db_path: str,
        database: DBProtocol | None,
        cache: CacheProtocol | None,
        travel_fn: Callable[..., list[str] | None],
        script_file: str,
    ) -> None:
        self.db_path = db_path
        self.database = database
        self.cache = cache
        self.travel_fn = travel_fn
        self.script_file = script_file
        self.logger = logger

    @staticmethod
    def create(
        db_factory: Callable[[str], DBProtocol] = datasource.DB,
        cache_factory: Callable[[Any], CacheProtocol] = cast(
            Callable[[Any], CacheProtocol], edgis_cache.EDGisCache.create
        ),
        travel_fn: Callable[..., list[str] | None] = ed_bfs.travel,
        script_file: str = __file__,
    ) -> "EDRouteService":
        load_dotenv()
        # Keep a stable default DB path while allowing env override.
        default_db_path = script_file.replace("src", "data").replace(".py", ".db")
        resolved_db_path = os.getenv("DB_LOCATION", default_db_path)
        logger.debug("Creating EDRouteService with db_path={}", resolved_db_path)
        service = EDRouteService(
            db_path=resolved_db_path,
            database=None,
            cache=None,
            travel_fn=travel_fn,
            script_file=script_file,
        )
        service.database = db_factory(resolved_db_path)
        service.cache = cache_factory(service.database)
        service.logger.info(
            "EDRouteService initialized with db_path={}", resolved_db_path
        )
        return service

    def init_datasource(self, import_dir: str = "./init") -> None:
        self.logger.info("Initializing datasource from {}", import_dir)
        self.database.init_datasource(import_dir)  # type: ignore[union-attr]

    def get_system_info(self, system_name: str) -> SystemInfo | None:
        if self.cache is None:
            self.logger.warning("Route cache is not initialized for get_system_info")
            return None
        self.logger.debug("Fetching system info via cache for system={}", system_name)
        return self.cache.find_system_info(system_name)

    def get_all_system_names(self) -> list[str]:
        if self.database is None:
            self.logger.warning("Database is not initialized for get_all_system_names")
            return []
        results = []
        system_infos = self.database.get_all_systems()
        for system_info in system_infos:
            results.append(system_info[constants.system_info_name_field])
        self.logger.debug("Collected {} system names", len(results))
        return results

    async def path(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        if self.cache is None:
            self.logger.warning("Route cache is not initialized for path")
            return None
        cache = self.cache
        self.logger.info(
            "Calculating path source={} destination={} max_systems={} min_distance={} max_distance={}",
            initial_system_name,
            destination_name,
            max_systems,
            min_distance,
            max_distance,
        )

        result: Future[list[str] | None] = Future()

        def _worker() -> None:
            # Run blocking BFS traversal off the event loop thread.
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
                result.set_result(route_result)
            except Exception as exc:
                result.set_exception(exc)

        threading.Thread(target=_worker, daemon=True).start()
        # Poll the worker Future so this async method stays non-blocking.
        while not result.done():
            await asyncio.sleep(0.01)
        route = result.result()
        self.logger.info("Path calculation complete found={}", route is not None)
        return route

    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float:
        self.logger.info(
            "Calculating distance between systems: {} and {}",
            system_name_one,
            system_name_two,
        )
        system_info_one = self.get_system_info(system_name_one)
        system_info_two = self.get_system_info(system_name_two)
        if system_info_one is None or system_info_two is None:
            missing_systems: list[str] = []
            if system_info_one is None:
                missing_systems.append(system_name_one)
            if system_info_two is None:
                missing_systems.append(system_name_two)
            message = f"Could not load system info for: {', '.join(missing_systems)}"
            self.logger.error(message)
            raise ValueError(message)

        # Distance is computed from each system's cartesian coordinates.
        coords1 = system_info_one[constants.system_info_coords_field]
        coords2 = system_info_two[constants.system_info_coords_field]

        # Euclidean distance in 3D space.
        distance = math.sqrt(
            (coords2["x"] - coords1["x"]) ** 2
            + (coords2["y"] - coords1["y"]) ** 2
            + (coords2["z"] - coords1["z"]) ** 2
        )
        self.logger.debug(
            "Distance calculated for {} -> {}: {}",
            system_name_one,
            system_name_two,
            distance,
        )
        return distance


if __name__ == "__main__":
    main()
