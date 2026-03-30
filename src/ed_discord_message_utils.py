from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Iterator, Sequence
from typing import TypeVar

import discord

from ed_protocols import DiscordContextProtocol, LoggingProtocol

T = TypeVar("T")


def chunked_sequence(items: Sequence[T], size: int = 5) -> Iterator[Sequence[T]]:
    """Yield a sequence in fixed-size chunks.

    Discord responses often need batching to stay readable or within message
    limits, so this helper slices any sequence into predictable chunk sizes
    while preserving the original order.
    """
    for index in range(0, len(items), size):
        yield items[index : index + size]


async def send_chunked_text(
    ctx: DiscordContextProtocol,
    text: str,
    chunk_size: int = 2000,
) -> None:
    """Send a long string to Discord in size-limited message chunks.

    The helper splits the text on raw character count using Discord's message
    limit and sends each chunk sequentially through the provided context.
    """
    for index in range(0, len(text), chunk_size):
        await ctx.send(text[index : index + chunk_size])


class DiscordProgressReporter:
    """Bridge thread-safe progress callbacks into Discord messages.

    Long-running route and cache operations emit synchronous progress strings.
    This adapter logs those messages immediately and schedules matching Discord
    sends onto the bot event loop from any calling thread.
    """

    def __init__(
        self,
        *,
        ctx: DiscordContextProtocol,
        logger: LoggingProtocol,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Store the Discord context, logger, and event loop for progress sends.

        The reporter needs all three collaborators because progress callbacks
        may come from worker threads that cannot directly await Discord I/O.
        """
        self._ctx = ctx
        self._logger = logger
        self._loop = loop

    def __call__(self, message: str) -> None:
        """Log a progress message and schedule it to be sent to Discord.

        The callable interface lets the reporter be passed directly as a
        progress callback while `run_coroutine_threadsafe` safely hands the send
        coroutine back to the event loop.
        """
        self._logger.info(message)
        send_future = asyncio.run_coroutine_threadsafe(
            self._ctx.send(message),
            self._loop,
        )
        send_future.add_done_callback(self._handle_send_result)

    def _handle_send_result(
        self,
        send_result: concurrent.futures.Future[discord.Message],
    ) -> None:
        """Log any failure from an asynchronously scheduled Discord send.

        Progress messages should never crash the underlying workload, so this
        callback inspects the future and records any exception through Loguru.
        """
        exc = send_result.exception()
        if exc is not None:
            self._logger.opt(exception=exc).error(
                "Failed to send progress update to Discord"
            )
