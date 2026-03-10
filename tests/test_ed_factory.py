import sys
import types

import pytest

import ed_datasource_factory
from ed_datasource_factory import EDDatasourceFactory


def main() -> None: ...


def test_resolve_datasource_type_prefers_explicit_arg(monkeypatch):
    monkeypatch.setenv("DATASOURCE_TYPE", "redis")
    assert ed_datasource_factory.resolve_datasource_type("tinydb") == "tinydb"


def test_resolve_datasource_type_uses_datasource_type_env(monkeypatch):
    monkeypatch.setenv("DATASOURCE_TYPE", "redis")
    assert ed_datasource_factory.resolve_datasource_type() == "redis"


def test_resolve_datasource_type_defaults_to_tinydb(monkeypatch):
    monkeypatch.delenv("DATASOURCE_TYPE", raising=False)
    assert ed_datasource_factory.resolve_datasource_type() == "tinydb"


def test_resolve_datasource_type_rejects_invalid_value(monkeypatch):
    monkeypatch.delenv("DATASOURCE_TYPE", raising=False)
    with pytest.raises(ValueError, match="Invalid DATASOURCE_TYPE value"):
        ed_datasource_factory.resolve_datasource_type("sqlite")


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
        ed_datasource_factory,
        "resolve_datasource_type",
        lambda datasource_type=None: "tinydb",
    )
    monkeypatch.setitem(
        sys.modules, "ed_tinydb", types.SimpleNamespace(EDTinyDB=FakeTinyDB)
    )

    result = ed_datasource_factory.create_datasource(datasource_name="tiny-name")
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
        ed_datasource_factory,
        "resolve_datasource_type",
        lambda datasource_type=None: "redis",
    )
    monkeypatch.setitem(
        sys.modules, "ed_redis", types.SimpleNamespace(EDRedis=FakeRedis)
    )

    result = ed_datasource_factory.create_datasource(datasource_name="redis-name")
    assert result == "redis-instance"
    assert captured["name"] == "redis-name"
    assert captured_logging_utils and captured_logging_utils[0] is not None


def test_datasource_factory_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDDatasourceFactory(logging_utils=None)


if __name__ == "__main__":
    main()
