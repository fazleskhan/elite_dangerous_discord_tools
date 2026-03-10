from __future__ import annotations

import math
import threading

from ed_constants import (
    system_info_coords_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)
from ed_protocols import GetSystemInfoProtocol, LoggingProtocol


class EDCalcSystemsDistanceService:
    def __init__(
        self,
        get_system_info_service: GetSystemInfoProtocol,
        logging_utils: LoggingProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if get_system_info_service is None:
            raise ValueError("get_system_info_service of type GetSystemInfoProtocol is required")
        else:
            self._get_system_info_service = get_system_info_service           
        self._coords_cache: dict[str, tuple[float, float, float]] = {}
        self._coords_cache_lock = threading.Lock()
        self._logging_utils.debug("EDCalcSystemsDistanceService initialized")        

    @staticmethod
    def create(
        get_system_info_service: GetSystemInfoProtocol,
        logging_utils: LoggingProtocol,
    ) -> "EDCalcSystemsDistanceService":
        return EDCalcSystemsDistanceService(get_system_info_service, logging_utils)

    def run(self, system_name_one: str, system_name_two: str) -> float:
        self._logging_utils.debug(
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
            self._logging_utils.error(message)
            raise ValueError(message)
        distance = math.sqrt(
            (coords_two[0] - coords_one[0]) ** 2
            + (coords_two[1] - coords_one[1]) ** 2
            + (coords_two[2] - coords_one[2]) ** 2
        )
        self._logging_utils.debug(
            "Distance calculated for {} -> {}: {}",
            system_name_one,
            system_name_two,
            distance,
        )
        return distance

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
