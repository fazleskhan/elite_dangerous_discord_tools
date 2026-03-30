import asyncio

import pytest

import ed_sync_async_bridge


def test_run_async_from_sync_handles_plain_calls_and_existing_event_loop() -> None:
    async def returns_value() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert (
        ed_sync_async_bridge.run_async_from_sync(returns_value(), value_key="result")
        == "ok"
    )

    async def run_inside_loop() -> str:
        return ed_sync_async_bridge.run_async_from_sync(
            returns_value(), value_key="result"
        )

    assert asyncio.run(run_inside_loop()) == "ok"


def test_run_async_from_sync_propagates_worker_thread_exceptions() -> None:
    async def raises() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    async def run_inside_loop() -> None:
        ed_sync_async_bridge.run_async_from_sync(raises(), value_key="result")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_inside_loop())
