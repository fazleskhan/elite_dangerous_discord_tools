from ed_constants import (
    system_info_coords_field,
    system_info_name_field,
    system_info_neighbors_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)
from ed_protocols import (
    DatasourceProtocol,
    FetchNeighborsFn,
    FetchSystemInfoFn,
    LoggingProtocol,
    SystemInfo,
)

"""Caching wrapper around EDGIS fetchers backed by the local datasource."""


def main() -> None: ...


class EDGisCache:
    """Cache layer with injected fetchers for easier testing."""

    def __init__(
        self,
        datasource: DatasourceProtocol,
        fetch_system_info_fn: FetchSystemInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
        *,
        logging_utils: LoggingProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self.logger = logging_utils
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        else:
            self.datasource = datasource
        if fetch_system_info_fn is None:
            raise ValueError(
                "fetch_system_info_fn of type FetchSystemInfoFn is required"
            )
        else:
            self.fetch_system_info_fn = fetch_system_info_fn
        if fetch_neighbors_fn is None:
            raise ValueError("fetch_neighbors_fn of type FetchNeighborsFn is required")
        else:
            self.fetch_neighbors_fn = fetch_neighbors_fn

    @staticmethod
    def create(
        datasource: DatasourceProtocol,
        logging_utils: LoggingProtocol,
        fetch_system_info_fn: FetchSystemInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
    ) -> "EDGisCache":
        return EDGisCache(
            datasource,
            fetch_system_info_fn,
            fetch_neighbors_fn,
            logging_utils=logging_utils,
        )

    # Cache-through read for system metadata.
    def find_system_info(self, system_name: str) -> SystemInfo | None:
        # Reuse cached entries before making a network call.
        system_info = self.datasource.get_system(system_name)

        # On a cache miss, fetch once and persist for future reads.
        if not system_info:
            self.logger.debug("Cache miss for system={}", system_name)
            if system_info := self.fetch_system_info_fn(system_name):
                self.datasource.insert_system(system_info)
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
        db_system_info = self.datasource.get_system(system_name)
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
                self.datasource.add_neighbors(system_info, neighbors)
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


if __name__ == "__main__":
    main()
