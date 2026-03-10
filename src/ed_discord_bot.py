from __future__ import annotations

import asyncio
import concurrent.futures
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import inspect
import time
from typing import Awaitable, Callable, Iterator, Sequence, TypeVar
import ed_datasource_factory
import edgis_cache
from edgis import EDGis
from ed_route_service_factory import EDRouteServiceFactory
from ed_logging_utils import EDLoggingUtils
from ed_constants import default_init_dir, discord_token_env
from ed_protocols import CacheProtocol, LoggingProtocol, RouteServiceProtocol

"""Discord command adapter for ED route and cache operations."""

T = TypeVar("T")


def main() -> None: ...


class EDDiscordBot:
    """Inversion‑of‑control wrapper around a :class:`commands.Bot` instance.

    Dependencies such as the routing module and configuration values are
    injected so that callers (tests, applications) can supply substitutes
    or mocks.
    """

    def __init__(
        self,
        ed_route_service: RouteServiceProtocol,
        token: str | None,
        bot: commands.Bot,
        logging_utils: LoggingProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if ed_route_service is None:
            raise ValueError(
                "ed_route_service of type RouteServiceProtocol is required"
            )
        else:
            self.ed_route = ed_route_service
        if token is None:
            raise ValueError("token of type str is required")
        else:
            self.token = token
        if bot is None:
            raise ValueError("bot of type commands.Bot is required")
        else:
            self.bot = bot
        self._logging_utils.debug(
            "Initializing DiscordBot with prefix={}", self.bot.command_prefix
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
        route_service: RouteServiceProtocol | None = None,
        cache: CacheProtocol | None = None,
        logging_utils: LoggingProtocol = EDLoggingUtils(),
        token: str | None = os.getenv(discord_token_env),
        bot: commands.Bot | None = None,
        intents_factory: discord.Intents | None = None,
        command_prefix: str = "!",
    ) -> "EDDiscordBot":
        load_dotenv()
        resolved_logging_utils = logging_utils
        resolved_logging_utils.debug(
            "Creating DiscordBot with command_prefix={}", command_prefix
        )
        resolved_route = route_service
        if resolved_route is None:
            datasource = ed_datasource_factory.create_datasource()
            gis = EDGis.create(resolved_logging_utils)
            cache = edgis_cache.EDGisCache.create(
                datasource,
                logging_utils=resolved_logging_utils,
                fetch_system_info_fn=gis.fetch_system_info,
                fetch_neighbors_fn=gis.fetch_neighbors,
            )
            resolved_route = EDRouteServiceFactory.create(
                datasource=datasource,
                cache=cache,
                logging_utils=resolved_logging_utils,
            )
        resolved_bot = bot or commands.Bot(
            command_prefix=command_prefix,
            intents=intents_factory or EDDiscordBot._default_intents(),
        )
        return EDDiscordBot(
            ed_route_service=resolved_route,
            token=token,
            bot=resolved_bot,
            logging_utils=resolved_logging_utils,
        )

    async def on_ready(self) -> None:
        user_name = self.bot.user.name if self.bot.user is not None else "<unknown>"
        self._logging_utils.info("Elite Dangerous Tools is ready: user={}", user_name)

    async def ping(self, ctx: commands.Context) -> None:
        start = time.perf_counter()
        self._logging_utils.debug("Received ping command")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(f"Pong ({elapsed_ms} ms)")

    async def _resolve(self, value: T | Awaitable[T]) -> T:
        # Allow both sync and async service implementations.
        if inspect.isawaitable(value):
            return await value
        return value

    async def system_info(self, ctx: commands.Context, arg: str) -> None:
        start = time.perf_counter()
        self._logging_utils.info("system_info command: system={}", arg)
        system_info = await self._resolve(self.ed_route.get_system_info(arg))
        self._logging_utils.debug(
            "system_info command completed: found={}", system_info is not None
        )
        s_info = str(system_info)
        # Discord message payloads are capped at 2000 characters.
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
        self._logging_utils.info(
            "calc_systems_distance command: system_one={} system_two={}",
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
        self._logging_utils.info(
            "path command: source={} destination={} max_system_count={} min_distance={} max_distance={}",
            initial_system_name,
            destination_system_name,
            max_system_count,
            min_distance,
            max_distance,
        )
        await ctx.send(
            f"Calculate Path between {initial_system_name} and {destination_system_name} with max system count {max_system_count} a min travel distance of {min_distance} and a max travel distance of {max_distance}...  This may take a while"
        )
        loop = asyncio.get_running_loop()

        def handle_progress_send_result(
            send_result: concurrent.futures.Future[None],
        ) -> None:
            # Progress sends happen from a worker-thread callback; surface
            # failures in logs instead of failing the command coroutine.
            exc = send_result.exception()
            if exc is not None:
                self._logging_utils.opt(exception=exc).error(
                    "Failed to send progress update to Discord"
                )

        def progress_callback(message: str) -> None:
            self._logging_utils.info(message)
            # Route progress callback executes off-loop; schedule send safely.
            send_future = asyncio.run_coroutine_threadsafe(ctx.send(message), loop)
            send_future.add_done_callback(handle_progress_send_result)

        route = await self._resolve(
            self.ed_route.path(
                initial_system_name,
                destination_system_name,
                max_systems=max_system_count,
                min_distance=min_distance,
                max_distance=max_distance,
                progress_callback=progress_callback,
            )
        )
        if not route:
            self._logging_utils.warning(
                "No route found: source={} destination={} max_system_count={}",
                initial_system_name,
                destination_system_name,
                max_system_count,
            )
            message = f"No Path found between {initial_system_name} and {destination_system_name} with max system count {max_system_count}"
        else:
            self._logging_utils.info(
                "Route found: source={} destination={} hops={}",
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
        self._logging_utils.info("dump_system_cache_names command")
        await ctx.send("Fetching all system names in cache... This may take a while")
        system_names = await self._resolve(self.ed_route.get_all_system_names())
        self._logging_utils.debug("Fetched {} cached system names", len(system_names))
        for chunk in self.chunked_system_list(system_names, size=10):
            system_names_message = ", ".join(chunk)
            await ctx.send(f"Systems in cache: {system_names_message}")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(
            f"Total number of systems in cache: {len(system_names)} ({elapsed_ms} ms)"
        )

    async def init_datasource(
        self, ctx: commands.Context, import_dir: str = default_init_dir
    ) -> None:
        start = time.perf_counter()
        self._logging_utils.info("init_datasource command: import_dir={}", import_dir)
        await self._resolve(self.ed_route.init_datasource(import_dir))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(f"Datasource initialized from {import_dir} ({elapsed_ms} ms)")

    async def bulk_load_cache(
        self,
        ctx: commands.Context,
        initial_systems: str,
        max_nodes_visited: int,
    ) -> None:
        start = time.perf_counter()
        initial_system_names = [
            system_name.strip()
            for system_name in initial_systems.split(",")
            if system_name.strip()
        ]
        self._logging_utils.info(
            "bulk_load_cache command: initial_systems={} max_nodes_visited={}",
            initial_system_names,
            max_nodes_visited,
        )
        await ctx.send(
            f"Bulk loading cache from seeds {initial_system_names} with max_nodes_visited={max_nodes_visited}... This may take a while"
        )
        loaded_systems = await self._resolve(
            self.ed_route.bulk_load_cache(
                initial_system_names,
                max_nodes_visited,
                progress_callback=lambda message: self._logging_utils.info(message),
            )
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        await ctx.send(
            f"Bulk load complete. Loaded {len(loaded_systems)} systems ({elapsed_ms} ms)"
        )

    def register_commands(self) -> None:
        self._logging_utils.debug("Registering bot commands")
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

        @self.bot.command()
        async def init_datasource(
            ctx: commands.Context, import_dir: str = default_init_dir
        ) -> None:
            return await self.init_datasource(ctx, import_dir)

        @self.bot.command()
        async def bulk_load_cache(
            ctx: commands.Context, initial_systems: str, max_nodes_visited: int
        ) -> None:
            return await self.bulk_load_cache(
                ctx,
                initial_systems,
                max_nodes_visited,
            )

    def run(self) -> None:
        """Start the bot using the configured token/logging.

        This call is intentionally side‑effecty, so tests in which we don't
        want to connect to Discord shouldn't use it.
        """
        if self.token is None:
            raise RuntimeError("DISCORD_TOKEN is not configured")
        self._logging_utils.info("Starting Discord bot run loop")
        self.bot.run(self.token, log_handler=None, log_level=None)


if __name__ == "__main__":
    main()
