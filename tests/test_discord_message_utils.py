import asyncio
import concurrent.futures
from typing import Any

import pytest

import discord_message_utils
from tests.helpers import ThreadSafeLogger


class FakeContext:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_send_chunked_text_splits_long_messages() -> None:
    ctx = FakeContext()

    await discord_message_utils.send_chunked_text(ctx, "abcdef", chunk_size=2)

    assert ctx.messages == ["ab", "cd", "ef"]


def test_chunked_sequence_returns_expected_slices() -> None:
    assert list(discord_message_utils.chunked_sequence(list(range(7)), size=3)) == [
        [0, 1, 2],
        [3, 4, 5],
        [6],
    ]


@pytest.mark.asyncio
async def test_discord_progress_reporter_logs_and_schedules_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = ThreadSafeLogger()
    ctx = FakeContext()
    loop = asyncio.get_running_loop()
    reporter = discord_message_utils.DiscordProgressReporter(
        ctx=ctx,
        logger=logger,
        loop=loop,
    )
    scheduled: list[str] = []

    def fake_run_coroutine_threadsafe(
        coro: Any, running_loop: asyncio.AbstractEventLoop
    ):
        assert running_loop is loop
        future: concurrent.futures.Future[None] = concurrent.futures.Future()

        async def consume() -> None:
            await coro
            scheduled.append("sent")
            future.set_result(None)

        loop.create_task(consume())
        return future

    monkeypatch.setattr(
        discord_message_utils.asyncio,
        "run_coroutine_threadsafe",
        fake_run_coroutine_threadsafe,
    )

    reporter("halfway")
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert scheduled == ["sent"]
    assert ctx.messages == ["halfway"]
    assert ("halfway", ()) in logger.messages("info")


def test_discord_progress_reporter_logs_send_failures() -> None:
    logger = ThreadSafeLogger()
    reporter = discord_message_utils.DiscordProgressReporter(
        ctx=FakeContext(),
        logger=logger,
        loop=asyncio.new_event_loop(),
    )
    future: concurrent.futures.Future[Any] = concurrent.futures.Future()
    future.set_exception(RuntimeError("send failed"))

    reporter._handle_send_result(future)

    assert (
        "Failed to send progress update to Discord",
        (),
    ) in logger.messages("error")
