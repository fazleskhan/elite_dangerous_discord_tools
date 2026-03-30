from __future__ import annotations

from ed_bfs_algo import EDBfsAlgo
from ed_bulk_load_algo import EDBulkLoadAlgo
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
)
from ed_route import EDRouteService
from ed_calc_systems_distance_service import EDCalcSystemsDistanceService
from ed_datasource_factory import EDDatasourceFactory
from ed_edgis_cache import EDGisCache
from ed_edgis import EDGis
from ed_get_all_system_names_service import EDGetAllSystemNamesService
from ed_get_system_info_service import EDGetSystemInfoService
from ed_init_datasource_service import EDInitDatasourceService
from ed_path_service import EDPathService


class EDRouteServiceFactory:
    """Build the application's default route-service object graph.

    The factory acts as the route-layer composition root. It preserves any
    caller-supplied collaborators, lazily creates the missing datasource and
    cache stack, and then assembles the focused services and algorithms that
    power route search, distance calculation, datasource initialization, and
    cache preloading.
    """

    @staticmethod
    def create(
        logger: LoggingProtocol | None,
        datasource: DatasourceProtocol | None = None,
        cache: CacheProtocol | None = None,
        bfs: BfsProtocol | None = None,
        init_datasource_service: InitDatasourceProtocol | None = None,
        get_system_info_service: GetSystemInfoProtocol | None = None,
        get_all_system_names_service: GetAllSystemNamesProtocol | None = None,
        bulk_load_cache_service: BulkLoadProtocol | None = None,
        path_service: PathProtocol | None = None,
        calc_systems_distance_service: CalcSystemsDistanceProtocol | None = None,
    ) -> EDRouteService:
        """Return an `EDRouteService` with defaults for any omitted collaborators.

        The method resolves dependencies in layers: datasource first, then the
        EDGIS-backed cache, then the focused route services, and finally the BFS
        and path orchestration pieces. That order lets callers override any
        individual layer while still getting a coherent default graph for the
        rest of the route stack.
        """
        if logger is None:
            raise ValueError("logger must not be null")
        resolved_datasource = datasource
        if resolved_datasource is None:
            # Storage selection stays inside the datasource factory so this
            # composition root remains protocol-oriented and backend-agnostic.
            datasource_factory = EDDatasourceFactory(logger=logger)
            resolved_datasource = datasource_factory.create_datasource()

        resolved_init_datasource_service = (
            init_datasource_service
            or EDInitDatasourceService(resolved_datasource, logger)
        )
        ed_edgis = EDGis(logger)
        # The cache is the bridge between persisted systems and EDGIS cache
        # misses, so later services can rely on one lookup surface.
        resolved_cache = cache or EDGisCache.create(
            resolved_datasource,
            logger,
            ed_edgis.fetch_system_info,
            ed_edgis.fetch_neighbors,
        )
        resolved_get_system_info_service = (
            get_system_info_service or EDGetSystemInfoService(resolved_cache, logger)
        )
        resolved_get_all_system_names_service = (
            get_all_system_names_service
            or EDGetAllSystemNamesService(resolved_datasource, logger)
        )
        resolved_calc_systems_distance_service = (
            calc_systems_distance_service
            or EDCalcSystemsDistanceService(
                resolved_get_system_info_service,
                logger,
            )
        )
        resolved_bfs = bfs or EDBfsAlgo(
            fetch_info_fn=resolved_cache.find_system_info,
            fetch_neighbors_fn=resolved_cache.find_system_neighbors,
            distance_fn=resolved_calc_systems_distance_service.run,
            logger=logger,
        )
        resolved_path_service = path_service or EDPathService(
            resolved_bfs,
            resolved_calc_systems_distance_service,
            logger,
        )
        resolved_bulk_load_cache_service = (
            bulk_load_cache_service
            or EDBulkLoadAlgo.create(
                resolved_cache,
                logger,
            )
        )
        logger.debug("Creating EDRouteService via datasource/cache composition")
        return EDRouteService(
            datasource=resolved_datasource,
            cache=resolved_cache,
            bfs=resolved_bfs,
            logger=logger,
            init_datasource_service=resolved_init_datasource_service,
            get_system_info_service=resolved_get_system_info_service,
            get_all_system_names_service=resolved_get_all_system_names_service,
            bulk_load_cache_service=resolved_bulk_load_cache_service,
            path_service=resolved_path_service,
            calc_systems_distance_service=resolved_calc_systems_distance_service,
        )
