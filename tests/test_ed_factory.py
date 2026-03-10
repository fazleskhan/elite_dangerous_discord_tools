import sys
import types

import pytest

import ed_factory
from ed_factory import EDDatasourceFactory


def main() -> None: ...


def test_resolve_datasource_type_prefers_explicit_arg(monkeypatch):
    monkeypatch.setenv("DATASOURCE_TYPE", "redis")
    assert ed_factory.resolve_datasource_type("tinydb") == "tinydb"


def test_resolve_datasource_type_uses_datasource_type_env(monkeypatch):
    monkeypatch.setenv("DATASOURCE_TYPE", "redis")
    assert ed_factory.resolve_datasource_type() == "redis"


def test_resolve_datasource_type_defaults_to_tinydb(monkeypatch):
    monkeypatch.delenv("DATASOURCE_TYPE", raising=False)
    assert ed_factory.resolve_datasource_type() == "tinydb"


def test_resolve_datasource_type_rejects_invalid_value(monkeypatch):
    monkeypatch.delenv("DATASOURCE_TYPE", raising=False)
    with pytest.raises(ValueError, match="Invalid DATASOURCE_TYPE value"):
        ed_factory.resolve_datasource_type("sqlite")


def test_create_datasource_uses_tinydb_backend(monkeypatch):
    captured: dict[str, str | None] = {"name": None}
    captured_logging_utils: list[object] = []

    class FakeTinyDB:
        @staticmethod
        def create(datasource_name: str | None = None, logging_utils=None):
            captured["name"] = datasource_name
            captured_logging_utils.append(logging_utils)
            return "tinydb-instance"

    monkeypatch.setattr(
        ed_factory,
        "resolve_datasource_type",
        lambda datasource_type=None: "tinydb",
    )
    monkeypatch.setitem(
        sys.modules, "ed_tinydb", types.SimpleNamespace(EDTinyDB=FakeTinyDB)
    )

    result = ed_factory.create_datasource(datasource_name="tiny-name")
    assert result == "tinydb-instance"
    assert captured["name"] == "tiny-name"
    assert captured_logging_utils and captured_logging_utils[0] is not None


def test_create_datasource_uses_redis_backend(monkeypatch):
    captured: dict[str, str | None] = {"name": None}
    captured_logging_utils: list[object] = []

    class FakeRedis:
        @staticmethod
        def create(datasource_name: str | None = None, logging_utils=None):
            captured["name"] = datasource_name
            captured_logging_utils.append(logging_utils)
            return "redis-instance"

    monkeypatch.setattr(
        ed_factory,
        "resolve_datasource_type",
        lambda datasource_type=None: "redis",
    )
    monkeypatch.setitem(
        sys.modules, "ed_redis", types.SimpleNamespace(EDRedis=FakeRedis)
    )

    result = ed_factory.create_datasource(datasource_name="redis-name")
    assert result == "redis-instance"
    assert captured["name"] == "redis-name"
    assert captured_logging_utils and captured_logging_utils[0] is not None


def test_create_route_service_composes_datasource_cache_and_route(monkeypatch):
    datasource_obj = object()
    cache_obj = object()
    travel_fn = object()

    monkeypatch.setattr(
        ed_factory,
        "create_datasource",
        lambda datasource_name=None, datasource_type=None: datasource_obj,
    )

    cache_calls: list[object] = []
    monkeypatch.setattr(
        ed_factory.edgis_cache.EDGisCache,
        "create",
        lambda db_obj, *, logging_utils: cache_calls.append(db_obj) or cache_obj,
    )

    route_calls: dict[str, object] = {}

    def fake_route_create(datasource, cache, travel_fn, logging_utils):
        route_calls["datasource"] = datasource
        route_calls["cache"] = cache
        route_calls["travel_fn"] = travel_fn
        route_calls["logging_utils"] = logging_utils
        return "route-service"

    monkeypatch.setattr(ed_factory.ed_route.EDRouteService, "create", fake_route_create)

    result = ed_factory.create_route_service(
        datasource_name="name",
        datasource_type="tinydb",
        travel_fn=travel_fn,  # type: ignore[arg-type]
    )

    assert result == "route-service"
    assert cache_calls == [datasource_obj]
    assert route_calls["datasource"] is datasource_obj
    assert route_calls["cache"] is cache_obj
    assert route_calls["travel_fn"] is travel_fn
    assert route_calls["logging_utils"] is not None


def test_datasource_factory_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDDatasourceFactory(logging_utils=None)


if __name__ == "__main__":
    main()
