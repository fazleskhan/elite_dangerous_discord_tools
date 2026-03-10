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
from ed_route_services import (
    EDCalcSystemsDistanceService,
    EDGetAllSystemNamesService,
    EDGetSystemInfoService,
    EDInitDatasourceService,
    EDPathService,
)
from ed_datasource_factory import EDDatasourceFactory
from edgis_cache import EDGisCache
from edgis import EDGis


class EDRouteServiceFactory:
    @staticmethod
    def create(
        logging_utils: LoggingProtocol,
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
        # Composition root for route operations: build concrete dependencies
        # only for arguments not already provided by callers/tests.
        datasource_factory = EDDatasourceFactory.create(logging_utils=logging_utils)
        datasource = datasource_factory.create_datasource()

        resolved_init_datasource_service = (
            init_datasource_service
            or EDInitDatasourceService.create(datasource, logging_utils)
        )
        edgis = EDGis.create(logging_utils)
        # Cache depends on external EDGIS fetchers plus local datasource.
        resolved_cache = cache or EDGisCache.create(
            datasource, logging_utils, edgis.fetch_system_info, edgis.fetch_neighbors
        )
        resolved_get_system_info_service = (
            get_system_info_service
            or EDGetSystemInfoService.create(resolved_cache, logging_utils)
        )
        resolved_get_all_system_names_service = (
            get_all_system_names_service
            or EDGetAllSystemNamesService.create(datasource, logging_utils)
        )
        resolved_calc_systems_distance_service = (
            calc_systems_distance_service
            or EDCalcSystemsDistanceService.create(
                resolved_get_system_info_service,
                logging_utils,
            )
        )
        resolved_bfs = bfs or EDBfsAlgo.create(
            resolved_cache.find_system_info,
            resolved_cache.find_system_neighbors,
            resolved_calc_systems_distance_service.run,
            logging_utils,
        )
        # Path and bulk-load services share cache/distance primitives but are
        # kept as separate delegates for simpler testing and reuse.
        resolved_path_service = path_service or EDPathService.create(
            resolved_bfs,
            resolved_calc_systems_distance_service,
            logging_utils,
        )
        resolved_bulk_load_cache_service = (
            bulk_load_cache_service
            or EDBulkLoadAlgo.create(
                resolved_cache,
                logging_utils,
            )
        )
        logging_utils.debug("Creating EDRouteService via datasource/cache composition")
        return EDRouteService(
            datasource=datasource,
            cache=resolved_cache,
            bfs=resolved_bfs,
            logging_utils=logging_utils,
            init_datasource_service=resolved_init_datasource_service,
            get_system_info_service=resolved_get_system_info_service,
            get_all_system_names_service=resolved_get_all_system_names_service,
            bulk_load_cache_service=resolved_bulk_load_cache_service,
            path_service=resolved_path_service,
            calc_systems_distance_service=resolved_calc_systems_distance_service,
        )
