from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Iterator, Sequence
from typing import TypeVar

import discord

from ed_protocols import DiscordContextProtocol, LoggingProtocol

T = TypeVar("T")


def chunked_sequence(items: Sequence[T], size: int = 5) -> Iterator[Sequence[T]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


async def send_chunked_text(
    ctx: DiscordContextProtocol,
    text: str,
    chunk_size: int = 2000,
) -> None:
    for index in range(0, len(text), chunk_size):
        await ctx.send(text[index : index + chunk_size])


class DiscordProgressReporter:
    def __init__(
        self,
        *,
        ctx: DiscordContextProtocol,
        logger: LoggingProtocol,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._ctx = ctx
        self._logger = logger
        self._loop = loop

    def __call__(self, message: str) -> None:
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
        exc = send_result.exception()
        if exc is not None:
            self._logger.opt(exception=exc).error(
                "Failed to send progress update to Discord"
            )
