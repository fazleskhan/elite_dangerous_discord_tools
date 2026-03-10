import sys
import types

import pytest

import ed_datasource_factory
from tests.helpers import ThreadSafeLogger


def test_factory_constructor_and_create_validate_logging_utils() -> None:
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        ed_datasource_factory.EDDatasourceFactory(None)  # type: ignore[arg-type]

    factory = ed_datasource_factory.EDDatasourceFactory.create(ThreadSafeLogger())
    assert isinstance(factory, ed_datasource_factory.EDDatasourceFactory)


def test_resolve_datasource_type_prefers_explicit_then_env_then_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATASOURCE_TYPE", "redis")
    assert ed_datasource_factory.resolve_datasource_type(" tinydb ") == "tinydb"
    assert ed_datasource_factory.resolve_datasource_type() == "redis"

    monkeypatch.delenv("DATASOURCE_TYPE", raising=False)
    assert ed_datasource_factory.resolve_datasource_type() == "tinydb"


def test_resolve_datasource_type_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Invalid DATASOURCE_TYPE value"):
        ed_datasource_factory.resolve_datasource_type("sqlite")


def test_create_datasource_uses_tinydb_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeTinyDB:
        @staticmethod
        def create(datasource_name=None, logging_utils=None):  # type: ignore[no-untyped-def]
            captured["name"] = datasource_name
            captured["logger"] = logging_utils
            return "tinydb"

    monkeypatch.setattr(ed_datasource_factory, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        ed_datasource_factory,
        "resolve_datasource_type",
        lambda *_args, **_kwargs: "tinydb",
    )
    monkeypatch.setitem(
        sys.modules, "ed_tinydb", types.SimpleNamespace(EDTinyDB=FakeTinyDB)
    )

    factory = ed_datasource_factory.EDDatasourceFactory(ThreadSafeLogger())
    assert factory.create_datasource(datasource_name="db.json") == "tinydb"
    assert captured["name"] == "db.json"
    assert captured["logger"] is not None


def test_create_datasource_uses_redis_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeRedis:
        @staticmethod
        def create(datasource_name=None, logging_utils=None):  # type: ignore[no-untyped-def]
            captured["name"] = datasource_name
            captured["logger"] = logging_utils
            return "redis"

    monkeypatch.setattr(ed_datasource_factory, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        ed_datasource_factory,
        "resolve_datasource_type",
        lambda *_args, **_kwargs: "redis",
    )
    monkeypatch.setitem(
        sys.modules, "ed_redis", types.SimpleNamespace(EDRedis=FakeRedis)
    )

    factory = ed_datasource_factory.EDDatasourceFactory(ThreadSafeLogger())
    assert factory.create_datasource(datasource_name="cache") == "redis"
    assert captured["name"] == "cache"
    assert captured["logger"] is not None


def test_module_create_datasource_uses_edloggingutils(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_with: list[object] = []

    class FakeFactory:
        def create_datasource(self, datasource_name=None, datasource_type=None):  # type: ignore[no-untyped-def]
            return (datasource_name, datasource_type)

    monkeypatch.setattr(ed_datasource_factory, "EDLoggingUtils", lambda: "logger")
    monkeypatch.setattr(
        ed_datasource_factory.EDDatasourceFactory,
        "create",
        staticmethod(
            lambda logging_utils: created_with.append(logging_utils) or FakeFactory()
        ),
    )

    assert ed_datasource_factory.create_datasource("name", "redis") == ("name", "redis")
    assert created_with == ["logger"]


def test_datasource_factory_main_is_a_noop() -> None:
    assert ed_datasource_factory.main() is None
