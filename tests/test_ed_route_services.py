import ed_route_services


def test_route_services_reexport_expected_symbols() -> None:
    assert "EDInitDatasourceService" in ed_route_services.__all__
    assert "EDPathService" in ed_route_services.__all__
    assert ed_route_services.EDInitDatasourceService is not None
    assert ed_route_services.EDBulkLoadCacheService is not None
