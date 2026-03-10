from __future__ import annotations

from ed_constants import default_init_dir
from ed_protocols import (
    BfsProtocol,
    BulkLoadProtocol,
    CalcSystemsDistanceProtocol,
    CacheProtocol,
    DatasourceProtocol,
    GetAllSystemNamesProtocol,
    GetSystemInfoProtocol,
    InitDatasourceProtocol,
    LoggingProtocol,
    PathProtocol,
    ProgressFn,
    SystemInfo,
)

"""Service layer that composes datasource/cache dependencies and route search."""


def main() -> None: ...


class EDRouteService:
    """Thin shim layer over delegate service classes."""

    def __init__(
        self,
        datasource: DatasourceProtocol,
        cache: CacheProtocol,
        bfs: BfsProtocol,
        logging_utils: LoggingProtocol,
        init_datasource_service: InitDatasourceProtocol,
        get_system_info_service: GetSystemInfoProtocol,
        get_all_system_names_service: GetAllSystemNamesProtocol,
        bulk_load_cache_service: BulkLoadProtocol,
        path_service: PathProtocol,
        calc_systems_distance_service: CalcSystemsDistanceProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self.logging_utils = logging_utils
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        else:
            self.database = datasource
        if cache is None:
            raise ValueError("cache of type CacheProtocol is required")
        else:
            self.cache = cache
        if init_datasource_service is None:
            raise ValueError(
                "init_datasource_service of type InitDatasourceProtocol is required"
            )
        else:
            self._init_datasource_service = init_datasource_service
        if get_system_info_service is None:
            raise ValueError(
                "get_system_info_service of type GetSystemInfoProtocol is required"
            )
        else:
            self._get_system_info_service = get_system_info_service
        if get_all_system_names_service is None:
            raise ValueError(
                "get_all_system_names_service of type GetAllSystemNamesProtocol is required"
            )
        else:
            self._get_all_system_names_service = get_all_system_names_service
        if bulk_load_cache_service is None:
            raise ValueError(
                "bulk_load_cache_service of type BulkLoadProtocol is required"
            )
        else:
            self._bulk_load_cache_service = bulk_load_cache_service
        if path_service is None:
            raise ValueError("path_service of type PathProtocol is required")
        else:
            self._path_service = path_service
        if calc_systems_distance_service is None:
            raise ValueError(
                "calc_systems_distance_service of type CalcSystemsDistanceProtocol is required"
            )
        else:
            self._calc_systems_distance_service = calc_systems_distance_service
        self._bfs = bfs

    def init_datasource(self, import_dir: str = default_init_dir) -> None:
        self._init_datasource_service.run(import_dir)

    def get_system_info(self, system_name: str) -> SystemInfo | None:
        return self._get_system_info_service.run(system_name)

    def get_all_system_names(self) -> list[str]:
        return self._get_all_system_names_service.run()

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        return self._bulk_load_cache_service.load(
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
        return await self._path_service.run(
            initial_system_name,
            destination_name,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )

    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float:
        return self._calc_systems_distance_service.run(system_name_one, system_name_two)

if __name__ == "__main__":
    main()
