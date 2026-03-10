import ed_route_service_factory
from tests.helpers import ThreadSafeLogger


def test_route_service_factory_builds_defaults(monkeypatch):  # type: ignore[no-untyped-def]
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
        ed_route_service_factory.EDDatasourceFactory,
        "create",
        staticmethod(
            lambda logging_utils: type(
                "Factory", (), {"create_datasource": lambda self: datasource}
            )()
        ),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGis,
        "create",
        staticmethod(
            lambda logging_utils: type(
                "GIS",
                (),
                {
                    "fetch_system_info": lambda self, name: {"name": name},
                    "fetch_neighbors": lambda self, x, y, z: [],
                },
            )()
        ),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGisCache,
        "create",
        staticmethod(
            lambda datasource, logging_utils, fetch_system_info_fn, fetch_neighbors_fn: cache
        ),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDInitDatasourceService,
        "create",
        staticmethod(lambda datasource, logging_utils: init_service),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGetSystemInfoService,
        "create",
        staticmethod(lambda cache, logging_utils: system_info_service),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGetAllSystemNamesService,
        "create",
        staticmethod(lambda datasource, logging_utils: system_names_service),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDCalcSystemsDistanceService,
        "create",
        staticmethod(lambda service, logging_utils: distance_service),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDBfsAlgo,
        "create",
        staticmethod(lambda *_args, **_kwargs: bfs),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDPathService,
        "create",
        staticmethod(lambda *_args, **_kwargs: path_service),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDBulkLoadAlgo,
        "create",
        staticmethod(lambda *_args, **_kwargs: bulk_service),
    )

    route_service = ed_route_service_factory.EDRouteServiceFactory.create(
        logging_utils=logger
    )

    assert route_service.database is datasource
    assert route_service.cache is cache
    assert route_service._bfs is bfs
    assert route_service._init_datasource_service is init_service
    assert route_service._get_system_info_service is system_info_service
    assert route_service._get_all_system_names_service is system_names_service
    assert route_service._bulk_load_cache_service is bulk_service
    assert route_service._path_service is path_service
    assert route_service._calc_systems_distance_service is distance_service


def test_route_service_factory_uses_supplied_overrides(monkeypatch):  # type: ignore[no-untyped-def]
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
        ed_route_service_factory.EDDatasourceFactory,
        "create",
        staticmethod(
            lambda logging_utils: type(
                "Factory", (), {"create_datasource": lambda self: supplied_datasource}
            )()
        ),
    )
    monkeypatch.setattr(
        ed_route_service_factory.EDGis,
        "create",
        staticmethod(lambda logging_utils: object()),
    )
    monkeypatch.setattr(
        ed_route_service_factory,
        "EDRouteService",
        ed_route_service_factory.EDRouteService,
    )

    route_service = ed_route_service_factory.EDRouteServiceFactory.create(
        logging_utils=logger,
        cache=supplied_cache,  # type: ignore[arg-type]
        bfs=supplied_bfs,  # type: ignore[arg-type]
        init_datasource_service=supplied_init,  # type: ignore[arg-type]
        get_system_info_service=supplied_info,  # type: ignore[arg-type]
        get_all_system_names_service=supplied_names,  # type: ignore[arg-type]
        bulk_load_cache_service=supplied_bulk,  # type: ignore[arg-type]
        path_service=supplied_path,  # type: ignore[arg-type]
        calc_systems_distance_service=supplied_distance,  # type: ignore[arg-type]
    )

    assert route_service.cache is supplied_cache
    assert route_service._bfs is supplied_bfs
    assert route_service._init_datasource_service is supplied_init
    assert route_service._get_system_info_service is supplied_info
    assert route_service._get_all_system_names_service is supplied_names
    assert route_service._bulk_load_cache_service is supplied_bulk
    assert route_service._path_service is supplied_path
    assert route_service._calc_systems_distance_service is supplied_distance
