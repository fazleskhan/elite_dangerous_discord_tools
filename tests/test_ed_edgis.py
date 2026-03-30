# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import asyncio

import aiohttp
import pytest

import ed_edgis
from tests.helpers import ThreadSafeLogger


@pytest.mark.asyncio
async def test_edgis_fetch_json_uses_client_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        async def __aenter__(self) -> "FakeResponse":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        def raise_for_status(self) -> None:
            captured["raised"] = True

        async def json(self) -> dict[str, str]:
            return {"name": "Sol"}

    class FakeSession:
        def __init__(self, timeout=None):
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str, params=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(ed_edgis.aiohttp, "ClientSession", FakeSession)
    result = await ed_edgis.EDGis._fetch_json("https://example", {"q": "Sol"})

    assert result == {"name": "Sol"}
    assert captured["url"] == "https://example"
    assert captured["params"] == {"q": "Sol"}


def test_edgis_validates_dependencies_and_create() -> None:
    with pytest.raises(ValueError, match="logger of type LoggingProtocol is required"):
        ed_edgis.EDGis(None)
    assert isinstance(ed_edgis.EDGis(ThreadSafeLogger()), ed_edgis.EDGis)


def test_run_async_handles_plain_and_event_loop_paths() -> None:
    async def returns_value() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert ed_edgis.EDGis._run_async(returns_value()) == "ok"

    async def run_inside_loop() -> str:
        return ed_edgis.EDGis._run_async(returns_value())

    assert asyncio.run(run_inside_loop()) == "ok"


def test_run_async_propagates_exceptions() -> None:
    async def raises() -> None:
        raise RuntimeError("boom")

    async def run_inside_loop() -> None:
        ed_edgis.EDGis._run_async(raises())

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_inside_loop())


def test_fetch_system_info_and_neighbors_handle_success_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = ThreadSafeLogger()
    gis = ed_edgis.EDGis(logger)
    monkeypatch.setattr(
        ed_edgis.EDGis,
        "_run_async",
        staticmethod(lambda coro: (coro.close(), {"name": "Sol"})[1]),
    )
    assert gis.fetch_system_info("Sol") == {"name": "Sol"}
    assert gis.fetch_neighbors(1, 2, 3) == {"name": "Sol"}

    def raise_client_error(coro):
        coro.close()
        raise aiohttp.ClientError("boom")

    monkeypatch.setattr(ed_edgis.EDGis, "_run_async", staticmethod(raise_client_error))
    assert gis.fetch_system_info("Sol") is None
    assert gis.fetch_neighbors(1, 2, 3) is None
    assert logger.messages("exception")


def test_fetch_methods_use_the_edgis_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = ThreadSafeLogger()
    gis = ed_edgis.EDGis(logger)
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_fetch_json(url: str, params: dict[str, object]) -> dict[str, str]:
        calls.append((url, params))
        return {"ok": "ok"}

    monkeypatch.setattr(ed_edgis.EDGis, "_fetch_json", staticmethod(fake_fetch_json))
    monkeypatch.setattr(
        ed_edgis.EDGis,
        "_run_async",
        staticmethod(lambda coro: asyncio.run(coro)),
    )

    assert gis.fetch_system_info("Sol") == {"ok": "ok"}
    assert gis.fetch_neighbors(1, 2, 3) == {"ok": "ok"}
    assert calls == [
        ("https://edgis.elitedangereuse.fr/coords", {"q": "Sol"}),
        ("https://edgis.elitedangereuse.fr/neighbors", {"x": 1, "y": 2, "z": 3}),
    ]


def test_fetch_system_info_integration_for_sol() -> None:
    logger = ThreadSafeLogger()
    gis = ed_edgis.EDGis(logger)

    result = gis.fetch_system_info("Sol")

    assert result is not None
    assert result["name"] == "Sol"
    assert result["coords"] == {"x": 0.0, "y": 0.0, "z": 0.0}


def test_fetch_neighbors_integration_for_origin() -> None:
    logger = ThreadSafeLogger()
    gis = ed_edgis.EDGis(logger)

    result = gis.fetch_neighbors(0, 0, 0)

    assert result is not None
    assert result
    assert any(
        neighbor["name"] == "Sol"
        and neighbor["coords"] == {"x": 0.0, "y": 0.0, "z": 0.0}
        and neighbor["distance"] == 0.0
        for neighbor in result
    )
