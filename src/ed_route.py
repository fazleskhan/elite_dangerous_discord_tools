from __future__ import annotations

from pathlib import Path

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


class EDRouteService:
    """Thin facade over delegate service classes."""

    def __init__(
        self,
        datasource: DatasourceProtocol,
        cache: CacheProtocol,
        bfs: BfsProtocol,
        logger: LoggingProtocol,
        init_datasource_service: InitDatasourceProtocol,
        get_system_info_service: GetSystemInfoProtocol,
        get_all_system_names_service: GetAllSystemNamesProtocol,
        bulk_load_cache_service: BulkLoadProtocol,
        path_service: PathProtocol,
        calc_systems_distance_service: CalcSystemsDistanceProtocol,
    ) -> None:
        """Store the composed route-layer collaborators.

        `EDRouteService` stays intentionally thin and delegates real work to
        specialized services, so the constructor validates and retains every
        collaborator needed for those forwarding methods.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self.logger = logger
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        self.database = datasource
        if cache is None:
            raise ValueError("cache of type CacheProtocol is required")
        self.cache = cache
        if init_datasource_service is None:
            raise ValueError(
                "init_datasource_service of type InitDatasourceProtocol is required"
            )
        self._init_datasource_service = init_datasource_service
        if get_system_info_service is None:
            raise ValueError(
                "get_system_info_service of type GetSystemInfoProtocol is required"
            )
        self._get_system_info_service = get_system_info_service
        if get_all_system_names_service is None:
            raise ValueError(
                "get_all_system_names_service of type GetAllSystemNamesProtocol is required"
            )
        self._get_all_system_names_service = get_all_system_names_service
        if bulk_load_cache_service is None:
            raise ValueError(
                "bulk_load_cache_service of type BulkLoadProtocol is required"
            )
        self._bulk_load_cache_service = bulk_load_cache_service
        if path_service is None:
            raise ValueError("path_service of type PathProtocol is required")
        self._path_service = path_service
        if calc_systems_distance_service is None:
            raise ValueError(
                "calc_systems_distance_service of type CalcSystemsDistanceProtocol is required"
            )
        self._calc_systems_distance_service = calc_systems_distance_service
        self._bfs = bfs

    def init_datasource(self, import_dir: str | Path = default_init_dir) -> None:
        """Initialize the datasource from the given directory.

        The route service keeps no initialization logic of its own; it simply
        forwards to the dedicated initialization service that owns locking and
        datasource coordination.
        """
        # Delegate orchestration details to focused service objects.
        self._init_datasource_service.run(import_dir)

    def get_system_info(self, system_name: str) -> SystemInfo | None:
        """Return cached or fetched metadata for one system.

        The route service forwards the request to the dedicated system-info
        service so callers can depend on one high-level route facade.
        """
        return self._get_system_info_service.run(system_name)

    def get_all_system_names(self) -> list[str]:
        """Return every known system name.

        The method delegates to the system-name service, which owns datasource
        access and extraction of names from stored records.
        """
        return self._get_all_system_names_service.run()

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        """Bulk load cache entries from the supplied seed systems.

        The route service exposes cache preloading as a top-level capability but
        delegates the actual graph walk and loading behavior to the injected
        bulk-load service.
        """
        # Keep EDRouteService thin: it routes calls, services implement behavior.
        return self._bulk_load_cache_service.load(
            initial_system_names,
            max_nodes_visited,
            progress_callback,
        )

    async def path(
        self,
        initial_system_name: str,
        destination_system_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        """Calculate a route between two systems.

        The method delegates to the dedicated path service, which adapts the BFS
        algorithm to the async surfaces used by the CLI and Discord layers.
        """
        return await self._path_service.run(
            initial_system_name,
            destination_system_name,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )

    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float:
        """Compute the distance between two systems.

        The route facade forwards to the distance service, which owns the
        coordinate lookup and Euclidean-distance calculation details.
        """
        return self._calc_systems_distance_service.run(system_name_one, system_name_two)
