import sys
import types

import pytest

import ed_factory


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

    class FakeTinyDB:
        @staticmethod
        def create(datasource_name: str | None = None):
            captured["name"] = datasource_name
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


def test_create_datasource_uses_redis_backend(monkeypatch):
    captured: dict[str, str | None] = {"name": None}

    class FakeRedis:
        @staticmethod
        def create(datasource_name: str | None = None):
            captured["name"] = datasource_name
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
        lambda db_obj: cache_calls.append(db_obj) or cache_obj,
    )

    route_calls: dict[str, object] = {}

    def fake_route_create(datasource, cache, travel_fn):
        route_calls["datasource"] = datasource
        route_calls["cache"] = cache
        route_calls["travel_fn"] = travel_fn
        return "route-service"

    monkeypatch.setattr(ed_factory.ed_route.EDRouteService, "create", fake_route_create)

    result = ed_factory.create_route_service(
        datasource_name="name",
        datasource_type="tinydb",
        travel_fn=travel_fn,  # type: ignore[arg-type]
    )

    assert result == "route-service"
    assert cache_calls == [datasource_obj]
    assert route_calls == {
        "datasource": datasource_obj,
        "cache": cache_obj,
        "travel_fn": travel_fn,
    }


if __name__ == "__main__":
    main()
