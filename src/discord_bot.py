from __future__ import annotations

import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import inspect
import time
from typing import Any, Awaitable, Iterator, Protocol, Sequence, TypeVar
import ed_route
from logging_utils import resolve_log_level

"""Discord command adapter for ED route and cache operations."""

T = TypeVar("T")
logger = logging.getLogger(__name__)


def main() -> None: ...


class RouteServiceProtocol(Protocol):
    def get_system_info(self, system_name: str) -> Any | Awaitable[Any]: ...
    def get_all_system_names(self) -> Sequence[str] | Awaitable[Sequence[str]]: ...
    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float | Awaitable[float]: ...
    def path(
        self,
        initial_system_name: str,
        destination_system_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
    ) -> Sequence[str] | Awaitable[Sequence[str]]: ...


class DiscordBot:
    """Inversion‑of‑control wrapper around a :class:`commands.Bot` instance.

    Dependencies such as the routing module and configuration values are
    injected so that callers (tests, applications) can supply substitutes
    or mocks.
    """

    def __init__(
        self,
        ed_route_service: RouteServiceProtocol,
        token: str | None,
        log_location: str,
        log_level: int,
        log_handler: logging.Handler,
        bot: commands.Bot,
    ) -> None:
        self.ed_route = ed_route_service
        self.token = token
        self.log_location = log_location
        self.log_level = log_level
        self.log_handler = log_handler
        self.bot = bot
        self.logger = logger
        self.logger.debug(
            "Initializing DiscordBot with prefix=%s", self.bot.command_prefix
        )
        self.bot.event(self.on_ready)
        self.register_commands()

    @staticmethod
    def _default_intents() -> discord.Intents:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        return intents

    @staticmethod
    def create(
        route_factory: RouteServiceProtocol = ed_route.EDRouteService.create(),
        token_factory: str | None = os.getenv("DISCORD_TOKEN"),
        log_location_factory: str = os.getenv("LOG_LOCATION", "discord_bot.log"),
        intents_factory: discord.Intents = _default_intents(),
        command_prefix: str = "!",
        log_level: int | None = None,
    ) -> DiscordBot:
        load_dotenv()
        logger.debug("Creating DiscordBot with command_prefix=%s", command_prefix)
        resolved_route = route_factory
        resolved_token = token_factory
        resolved_log_location = log_location_factory
        resolved_log_level = (
            log_level if log_level is not None else resolve_log_level(logging.DEBUG)
        )
        resolved_log_handler = logging.FileHandler(
            filename=resolved_log_location, encoding="utf-8", mode="w"
        )
        resolved_bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents_factory,
        )
        return DiscordBot(
            ed_route_service=resolved_route,
            token=resolved_token,
            log_location=resolved_log_location,
            log_level=resolved_log_level,
            log_handler=resolved_log_handler,
            bot=resolved_bot,
        )

    async def on_ready(self) -> None:
        self.logger.info("Elite Dangerous Tools is ready: user=%s", self.bot.user.name)

    async def ping(self, ctx: commands.Context) -> None:
        start = time.perf_counter()
        self.logger.debug("Received ping command")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(f"Pong ({elapsed_ms} ms)")

    async def _resolve(self, value: T | Awaitable[T]) -> T:
        # Allow both sync and async service implementations.
        if inspect.isawaitable(value):
            return await value
        return value

    async def system_info(self, ctx: commands.Context, arg: str) -> None:
        start = time.perf_counter()
        self.logger.info("system_info command: system=%s", arg)
        system_info = await self._resolve(self.ed_route.get_system_info(arg))
        self.logger.debug(
            "system_info command completed: found=%s", system_info is not None
        )
        s_info = str(system_info)
        if len(s_info) <= 2000:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await ctx.send(f"{arg}: {s_info} ({elapsed_ms} ms)")
        else:
            chunks = [s_info[i : i + 2000] for i in range(0, len(s_info), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await ctx.send(f"Execution time: {elapsed_ms} ms")

    async def calc_systems_distance(
        self,
        ctx: commands.Context,
        system_name_one: str,
        system_name_two: str,
    ) -> None:
        start = time.perf_counter()
        self.logger.info(
            "calc_systems_distance command: system_one=%s system_two=%s",
            system_name_one,
            system_name_two,
        )
        distance = await self._resolve(
            self.ed_route.calc_systems_distance(system_name_one, system_name_two)
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(
            f"Distance between {system_name_one} and {system_name_two}: {distance} ({elapsed_ms} ms)"
        )

    async def path(
        self,
        ctx: commands.Context,
        initial_system_name: str,
        destination_system_name: str,
        max_system_count: int = 100,
        min_distance: int = 0,
        max_distance: int = 10000,
    ) -> None:
        start = time.perf_counter()
        self.logger.info(
            "path command: source=%s destination=%s max_system_count=%s min_distance=%s max_distance=%s",
            initial_system_name,
            destination_system_name,
            max_system_count,
            min_distance,
            max_distance,
        )
        await ctx.send(
            f"Calculate Path between {initial_system_name} and {destination_system_name} with max system count {max_system_count} a min travel distance of {min_distance} and a max travel distance of {max_distance}...  This may take a while"
        )
        route = await self._resolve(
            self.ed_route.path(
                initial_system_name,
                destination_system_name,
                max_systems=max_system_count,
                min_distance=min_distance,
                max_distance=max_distance,
            )
        )
        if not route:
            self.logger.warning(
                "No route found: source=%s destination=%s max_system_count=%s",
                initial_system_name,
                destination_system_name,
                max_system_count,
            )
            message = f"No Path found between {initial_system_name} and {destination_system_name} with max system count {max_system_count}"
        else:
            self.logger.info(
                "Route found: source=%s destination=%s hops=%s",
                initial_system_name,
                destination_system_name,
                len(route),
            )
            route_message = " → ".join(route)
            message = f"Route from {initial_system_name} to {destination_system_name}: {route_message} "
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(f"{message}({elapsed_ms} ms)")

    def chunked_system_list(
        self, system_list: Sequence[str], size: int = 5
    ) -> Iterator[Sequence[str]]:
        for i in range(0, len(system_list), size):
            yield system_list[i : i + size]

    async def dump_system_cache_names(self, ctx: commands.Context) -> None:
        start = time.perf_counter()
        self.logger.info("dump_system_cache_names command")
        await ctx.send("Fetching all system names in cache... This may take a while")
        system_names = await self._resolve(self.ed_route.get_all_system_names())
        self.logger.debug("Fetched %s cached system names", len(system_names))
        for chunk in self.chunked_system_list(system_names, size=10):
            system_names_message = ", ".join(chunk)
            await ctx.send(f"Systems in cache: {system_names_message}")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(
            f"Total number of systems in cache: {len(system_names)} ({elapsed_ms} ms)"
        )

    def register_commands(self) -> None:
        self.logger.debug("Registering bot commands")
        # ``discord.ext.commands`` expects plain callables whose first
        # parameter is ``ctx`` (plus any user arguments).  Using a bound
        # method would insert ``self`` as the first argument, causing
        # the framework to complain about the signature.  To keep the
        # instance methods while satisfying the API we register small
        # wrappers that delegate back to ``self``.

        @self.bot.command()
        async def ping(ctx: commands.Context) -> None:
            return await self.ping(ctx)

        @self.bot.command()
        async def system_info(ctx: commands.Context, arg: str) -> None:
            return await self.system_info(ctx, arg)

        @self.bot.command()
        async def path(
            ctx: commands.Context,
            initial_system_name: str,
            destination_system_name: str,
            max_system_count: int = 100,
            min_distance: int = 0,
            max_distance: int = 10000,
        ) -> None:
            return await self.path(
                ctx,
                initial_system_name,
                destination_system_name,
                max_system_count,
                min_distance,
                max_distance,
            )

        @self.bot.command()
        async def calc_systems_distance(
            ctx: commands.Context, system_name_one: str, system_name_two: str
        ) -> None:
            return await self.calc_systems_distance(
                ctx, system_name_one, system_name_two
            )

        @self.bot.command()
        async def dump_system_cache_names(ctx: commands.Context) -> None:
            return await self.dump_system_cache_names(ctx)

    def run(self) -> None:
        """Start the bot using the configured token/logging.

        This call is intentionally side‑effecty, so tests in which we don't
        want to connect to Discord shouldn't use it.
        """
        self.logger.info("Starting Discord bot run loop")
        self.bot.run(self.token, log_handler=self.log_handler, log_level=self.log_level)


if __name__ == "__main__":
    main()
