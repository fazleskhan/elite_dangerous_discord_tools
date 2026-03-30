# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import ed_route_service_factory
from tests.helpers import ThreadSafeLogger


def test_route_service_factory_builds_defaults(monkeypatch):
    logger = ThreadSafeLogger()
    datasource = object()
    cache = type(
        "Cache",
        (),
        {
            "find_system_info": lambda self, name: {"name": name},
            "find_system_neighbors": lambda self, info: [],
        },
    )()
    init_service = object()
    system_info_service = object()
    system_names_service = object()
    distance_service = type("Distance", (), {"run": lambda self, one, two: 5.0})()
    bfs = object()
    path_service = object()
    bulk_service = object()

    monkeypatch.setattr(
        ed_route_service_factory,
        "EDDatasourceFactory",
        lambda logger: type(
            "Factory", (), {"create_datasource": lambda self: datasource}
        )(),
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDGis",
        lambda logger: type(
            "GIS",
            (),
            {
                "fetch_system_info": lambda self, name: {"name": name},
                "fetch_neighbors": lambda self, x, y, z: [],
            },
        )(),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGisCache,
        "create",
        staticmethod(
            lambda datasource, logger, fetch_system_info_fn, fetch_neighbors_fn: cache
        ),
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDInitDatasourceService",
        lambda datasource, logger: init_service,
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDGetSystemInfoService",
        lambda cache, logger: system_info_service,
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDGetAllSystemNamesService",
        lambda datasource, logger: system_names_service,
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDCalcSystemsDistanceService",
        lambda service, logger: distance_service,
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDBfsAlgo",
        lambda *args, **kwargs: bfs,
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDPathService",
        lambda *args, **kwargs: path_service,
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDBulkLoadAlgo,
        "create",
        staticmethod(lambda *_args, **_kwargs: bulk_service),
    )

    route_service = ed_route_service_factory.EDRouteServiceFactory.create(logger=logger)

    assert route_service.database is datasource
    assert route_service.cache is cache
    assert route_service._bfs is bfs
    assert route_service._init_datasource_service is init_service
    assert route_service._get_system_info_service is system_info_service
    assert route_service._get_all_system_names_service is system_names_service
    assert route_service._bulk_load_cache_service is bulk_service
    assert route_service._path_service is path_service
    assert route_service._calc_systems_distance_service is distance_service


def test_route_service_factory_uses_supplied_overrides(monkeypatch):
    logger = ThreadSafeLogger()
    supplied_datasource = object()
    supplied_cache = object()
    supplied_bfs = object()
    supplied_init = object()
    supplied_info = object()
    supplied_names = object()
    supplied_bulk = object()
    supplied_path = object()
    supplied_distance = object()

    monkeypatch.setattr(
        ed_route_service_factory,
        "EDDatasourceFactory",
        lambda logger: type(
            "Factory", (), {"create_datasource": lambda self: supplied_datasource}
        )(),
    )
    monkeypatch.setattr(ed_route_service_factory, "EDGis", lambda logger: object())
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDRouteService",
        ed_route_service_factory.EDRouteService,
    )

    route_service = ed_route_service_factory.EDRouteServiceFactory.create(
        logger=logger,
        datasource=supplied_datasource,
        cache=supplied_cache,
        bfs=supplied_bfs,
        init_datasource_service=supplied_init,
        get_system_info_service=supplied_info,
        get_all_system_names_service=supplied_names,
        bulk_load_cache_service=supplied_bulk,
        path_service=supplied_path,
        calc_systems_distance_service=supplied_distance,
    )

    assert route_service.database is supplied_datasource
    assert route_service.cache is supplied_cache
    assert route_service._bfs is supplied_bfs
    assert route_service._init_datasource_service is supplied_init
    assert route_service._get_system_info_service is supplied_info
    assert route_service._get_all_system_names_service is supplied_names
    assert route_service._bulk_load_cache_service is supplied_bulk
    assert route_service._path_service is supplied_path
    assert route_service._calc_systems_distance_service is supplied_distance
