from edgis import fetch_system_info, fetch_neighbors
import constants
from typing import Any, Callable, Protocol


SystemInfo = dict[str, Any]
FetchSystemInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[
    [float | int, float | int, float | int], list[SystemInfo] | None
]


class DBProtocol(Protocol):
    def get_system(self, system_name: str) -> SystemInfo | None: ...
    def insert_system(self, system_info: SystemInfo) -> int | None: ...
    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> list[int]: ...


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

    @staticmethod
    def create(
        db_obj: DBProtocol,
        fetch_system_info_fn: FetchSystemInfoFn = fetch_system_info,
        fetch_neighbors_fn: FetchNeighborsFn = fetch_neighbors,
    ) -> "EDGisCache":
        return EDGisCache(db_obj, fetch_system_info_fn, fetch_neighbors_fn)

    # Provides cache abstraction layer to save system
    # information localy and reduce edgris calls
    def find_system_info(self, system_name: str) -> SystemInfo | None:
        # checking if the system has already been fetched
        system_info = self.db.get_system(system_name)

        # first time requesting the system form edgis
        if not system_info:
            if system_info := self.fetch_system_info_fn(system_name):
                self.db.insert_system(system_info)

        return system_info

    # Provides cache abstraction layer to save system neighbor
    # information localy and reduce edgris calls
    def find_system_neighbors(self, system_info: SystemInfo) -> list[SystemInfo] | None:
        # make sure working with that latest db system_info
        db_system_info = self.db.get_system(
            system_info[constants.system_info_name_field]
        )
        neighbors = (
            db_system_info.get(constants.system_info_neighbors_field, None)
            if db_system_info
            else None
        )
        # If the neighbors have already been loaded don't load again
        if not neighbors:
            x = system_info[constants.system_info_coords_field][
                constants.system_info_x_field
            ]
            y = system_info[constants.system_info_coords_field][
                constants.system_info_y_field
            ]
            z = system_info[constants.system_info_coords_field][
                constants.system_info_z_field
            ]
            neighbors = self.fetch_neighbors_fn(x, y, z)
            self.db.add_neighbors(system_info, neighbors)
        return neighbors


if __name__ == "__main__":
    main()
