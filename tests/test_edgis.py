import asyncio

import aiohttp
import pytest

import edgis
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
        def __init__(self, timeout=None):  # type: ignore[no-untyped-def]
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str, params=None):  # type: ignore[no-untyped-def]
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(edgis.aiohttp, "ClientSession", FakeSession)
    result = await edgis.EDGis._fetch_json("https://example", {"q": "Sol"})

    assert result == {"name": "Sol"}
    assert captured["url"] == "https://example"
    assert captured["params"] == {"q": "Sol"}


def test_edgis_validates_dependencies_and_create() -> None:
    with pytest.raises(
        ValueError, match="logging_utils of type LoggingProtocol is required"
    ):
        edgis.EDGis(None)  # type: ignore[arg-type]
    assert isinstance(edgis.EDGis.create(ThreadSafeLogger()), edgis.EDGis)


def test_run_async_handles_plain_and_event_loop_paths() -> None:
    async def returns_value() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert edgis.EDGis._run_async(returns_value()) == "ok"

    async def run_inside_loop() -> str:
        return edgis.EDGis._run_async(returns_value())

    assert asyncio.run(run_inside_loop()) == "ok"


def test_run_async_propagates_exceptions() -> None:
    async def raises() -> None:
        raise RuntimeError("boom")

    async def run_inside_loop() -> None:
        edgis.EDGis._run_async(raises())

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_inside_loop())


def test_fetch_system_info_and_neighbors_handle_success_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = ThreadSafeLogger()
    gis = edgis.EDGis(logger)
    monkeypatch.setattr(
        edgis.EDGis,
        "_run_async",
        staticmethod(lambda coro: (coro.close(), {"name": "Sol"})[1]),
    )
    assert gis.fetch_system_info("Sol") == {"name": "Sol"}
    assert gis.fetch_neighbors(1, 2, 3) == {"name": "Sol"}

    def raise_client_error(coro):  # type: ignore[no-untyped-def]
        coro.close()
        raise aiohttp.ClientError("boom")

    monkeypatch.setattr(edgis.EDGis, "_run_async", staticmethod(raise_client_error))
    assert gis.fetch_system_info("Sol") is None
    assert gis.fetch_neighbors(1, 2, 3) is None
    assert logger.messages("exception")


def test_edgis_main_is_a_noop() -> None:
    assert edgis.main() is None
