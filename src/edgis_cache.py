from edgis import fetch_system_info, fetch_neighbors
from loguru import logger
from typing import Any, Callable, Protocol
from ed_constants import (
    system_info_coords_field,
    system_info_name_field,
    system_info_neighbors_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)

"""Caching wrapper around EDGIS fetchers backed by the local DB."""


SystemInfo = dict[str, Any]
FetchSystemInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[
    [float | int, float | int, float | int], list[SystemInfo] | None
]


class DBProtocol(Protocol):
    def get_system(self, system_name: str) -> SystemInfo | None: ...
    def insert_system(self, system_info: SystemInfo) -> None: ...
    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None: ...


def main() -> None: ...


class EDGisCache:
    """Cache layer with injected fetchers for easier testing."""

    def __init__(
        self,
        db: DBProtocol,
        fetch_system_info_fn: FetchSystemInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
    ) -> None:
        self.db = db
        self.fetch_system_info_fn = fetch_system_info_fn
        self.fetch_neighbors_fn = fetch_neighbors_fn
        self.logger = logger

    @staticmethod
    def create(
        db_obj: DBProtocol,
        fetch_system_info_fn: FetchSystemInfoFn = fetch_system_info,
        fetch_neighbors_fn: FetchNeighborsFn = fetch_neighbors,
    ) -> "EDGisCache":
        return EDGisCache(db_obj, fetch_system_info_fn, fetch_neighbors_fn)

    # Cache-through read for system metadata.
    def find_system_info(self, system_name: str) -> SystemInfo | None:
        # Reuse cached entries before making a network call.
        system_info = self.db.get_system(system_name)

        # On a cache miss, fetch once and persist for future reads.
        if not system_info:
            self.logger.debug("Cache miss for system={}", system_name)
            if system_info := self.fetch_system_info_fn(system_name):
                self.db.insert_system(system_info)
                self.logger.debug("Inserted system={} into cache", system_name)
            else:
                self.logger.warning(
                    "Failed to fetch system={} on cache miss", system_name
                )
        else:
            self.logger.debug("Cache hit for system={}", system_name)

        return system_info

    # Cache-through read for neighboring systems.
    def find_system_neighbors(self, system_info: SystemInfo) -> list[SystemInfo] | None:
        system_name = system_info[system_info_name_field]
        # Always re-read from DB in case neighbors were populated by a prior call.
        db_system_info = self.db.get_system(system_name)
        neighbors = (
            db_system_info.get(system_info_neighbors_field, None)
            if db_system_info
            else None
        )
        # Fetch neighbors once per system and store them in the DB cache.
        if not neighbors:
            self.logger.debug("Neighbor cache miss for system={}", system_name)
            x = system_info[system_info_coords_field][system_info_x_field]
            y = system_info[system_info_coords_field][system_info_y_field]
            z = system_info[system_info_coords_field][system_info_z_field]
            neighbors = self.fetch_neighbors_fn(x, y, z)
            if neighbors is not None:
                self.db.add_neighbors(system_info, neighbors)
                self.logger.debug(
                    "Cached {} neighbors for system={}", len(neighbors), system_name
                )
            else:
                self.logger.warning(
                    "Failed to fetch neighbors for system={}", system_name
                )
        else:
            self.logger.debug("Neighbor cache hit for system={}", system_name)
        return neighbors


class EDCache(EDGisCache):
    """Project-level cache class with explicit IoC create signature."""

    @staticmethod
    def create(
        db_obj: DBProtocol,
        gis: Any,
        logging_utils: Any,
    ) -> "EDCache":
        return EDCache(
            db_obj,
            fetch_system_info_fn=gis.fetch_system_info,
            fetch_neighbors_fn=gis.fetch_neighbors,
        )


if __name__ == "__main__":
    main()
