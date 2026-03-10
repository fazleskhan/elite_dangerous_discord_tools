from __future__ import annotations

import asyncio
import math
import threading
from typing import Any

from ed_bfs import EDBfs
from ed_bulk_load_algo import EDBulkLoadAlgo
from ed_constants import (
    default_init_dir,
    system_info_coords_field,
    system_info_name_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)
from ed_protocols import (
    CacheProtocol,
    DatasourceProtocol,
    LoggingProtocol,
    ProgressFn,
    SystemInfo,
)
from ed_logging_utils import EDLoggingUtils


class EDInitDatasourceService:
    def __init__(self, database: DatasourceProtocol, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        self._database = database
        self._lock = threading.RLock()
        self._logging_utils = logging_utils

    @staticmethod
    def create(
        database: DatasourceProtocol, logging_utils: LoggingProtocol
    ) -> "EDInitDatasourceService":
        return EDInitDatasourceService(database, logging_utils)

    def run(self, import_dir: str = default_init_dir) -> None:
        with self._lock:
            self._database.init_datasource(import_dir)


class EDGetSystemInfoService:
    def __init__(self, cache: CacheProtocol, logging_utils: LoggingProtocol) -> None:
        self._cache = cache
        self._lock = threading.RLock()
        self._logging_utils = logging_utils

    @staticmethod
    def create(cache: CacheProtocol, logging_utils: LoggingProtocol) -> "EDGetSystemInfoService":
        return EDGetSystemInfoService(cache, logging_utils)

    def run(self, system_name: str) -> SystemInfo | None:
        with self._lock:
            return self._cache.find_system_info(system_name)


class EDGetAllSystemNamesService:
    def __init__(self, database: DatasourceProtocol, logging_utils: LoggingProtocol) -> None:
        self._database = database
        self._lock = threading.RLock()
        self._logging_utils = logging_utils

    @staticmethod
    def create(
        database: DatasourceProtocol, logging_utils: LoggingProtocol
    ) -> "EDGetAllSystemNamesService":
        return EDGetAllSystemNamesService(database, logging_utils)

    def run(self) -> list[str]:
        with self._lock:
            system_infos = self._database.get_all_systems()
        return [
            system_info[system_info_name_field]
            for system_info in system_infos
            if system_info_name_field in system_info
        ]


class EDCalcSystemsDistanceService:
    def __init__(
        self,
        get_system_info_service: EDGetSystemInfoService,
        logging_utils: LoggingProtocol,
    ) -> None:
        self._get_system_info_service = get_system_info_service
        self._coords_cache: dict[str, tuple[float, float, float]] = {}
        self._coords_cache_lock = threading.Lock()
        self._logging_utils = logging_utils

    @staticmethod
    def create(
        get_system_info_service: EDGetSystemInfoService,
        logging_utils: LoggingProtocol,
    ) -> "EDCalcSystemsDistanceService":
        return EDCalcSystemsDistanceService(get_system_info_service, logging_utils)

    def run(self, system_name_one: str, system_name_two: str) -> float:
        coords_one = self._get_system_coords(system_name_one)
        coords_two = self._get_system_coords(system_name_two)
        if coords_one is None or coords_two is None:
            missing_systems: list[str] = []
            if coords_one is None:
                missing_systems.append(system_name_one)
            if coords_two is None:
                missing_systems.append(system_name_two)
            message = f"Could not load system info for: {', '.join(missing_systems)}"
            self._logging_utils.error(message)
            raise ValueError(message)
        return math.sqrt(
            (coords_two[0] - coords_one[0]) ** 2
            + (coords_two[1] - coords_one[1]) ** 2
            + (coords_two[2] - coords_one[2]) ** 2
        )

    def _get_system_coords(self, system_name: str) -> tuple[float, float, float] | None:
        with self._coords_cache_lock:
            cached = self._coords_cache.get(system_name)
        if cached is not None:
            return cached

        system_info = self._get_system_info_service.run(system_name)
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


class EDPathService:
    def __init__(
        self,
        bfs: EDBfs,
        calc_distance_service: EDCalcSystemsDistanceService,
        logging_utils: LoggingProtocol,
    ) -> None:
        self._bfs = bfs
        self._calc_distance_service = calc_distance_service
        self._logging_utils = logging_utils

    @staticmethod
    def create(
        bfs: EDBfs,
        calc_distance_service: EDCalcSystemsDistanceService,
        logging_utils: LoggingProtocol,
    ) -> "EDPathService":
        return EDPathService(bfs, calc_distance_service, logging_utils)

    async def run(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        return await asyncio.to_thread(
            self._bfs.travel,
            initial_system_name,
            destination_name,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )


class EDBulkLoadCacheService:
    def __init__(self, bulk_load: EDBulkLoadAlgo, logging_utils: LoggingProtocol) -> None:
        self._bulk_load = bulk_load
        self._logging_utils = logging_utils

    @staticmethod
    def create(
        bulk_load: EDBulkLoadAlgo, logging_utils: LoggingProtocol
    ) -> "EDBulkLoadCacheService":
        return EDBulkLoadCacheService(bulk_load, logging_utils)

    def run(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        return self._bulk_load.load(
            initial_system_names=initial_system_names,
            max_nodes_visited=max_nodes_visited,
            progress_callback=progress_callback,
        )
