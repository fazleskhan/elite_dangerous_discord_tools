import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import inspect
import ed_route


class DiscordBot:
    """Inversion‑of‑control wrapper around a :class:`commands.Bot` instance.

    Dependencies such as the routing module and configuration values are
    injected so that callers (tests, applications) can supply substitutes
    or mocks.
    """

    def __init__(self, ed_route_service, token, log_location, log_level, log_handler, bot):
        self.ed_route = ed_route_service
        self.token = token
        self.log_location = log_location
        self.log_level = log_level
        self.log_handler = log_handler
        self.bot = bot
        self.bot.event(self.on_ready)
        self.register_commands()

    @staticmethod
    def _default_intents():
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        return intents

    @staticmethod
    def create(
        ed_route_service=None,
        ed_route_module=None,
        command_prefix="!",
        token=None,
        log_location=None,
        intents=None,
        log_level=logging.DEBUG,
    ):
        load_dotenv()
        if ed_route_service:
            resolved_route = ed_route_service
        elif ed_route_module:
            resolved_route = ed_route_module
        elif hasattr(ed_route, "EDRouteService"):
            if hasattr(ed_route.EDRouteService, "create"):
                resolved_route = ed_route.EDRouteService.create()
            else:
                resolved_route = ed_route.EDRouteService()
        elif hasattr(ed_route, "EdRouteService"):
            if hasattr(ed_route.EdRouteService, "create"):
                resolved_route = ed_route.EdRouteService.create()
            else:
                resolved_route = ed_route.EdRouteService()
        else:
            # Backward-compatible fallback for module-level ed_route helpers.
            resolved_route = ed_route
        resolved_token = token or os.getenv("DISCORD_TOKEN")
        resolved_log_location = log_location or os.getenv(
            "LOG_LOCATION", "discord_bot.log"
        )
        resolved_log_handler = logging.FileHandler(
            filename=resolved_log_location, encoding="utf-8", mode="w"
        )
        resolved_bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents or DiscordBot._default_intents(),
        )
        return DiscordBot(
            ed_route_service=resolved_route,
            token=resolved_token,
            log_location=resolved_log_location,
            log_level=log_level,
            log_handler=resolved_log_handler,
            bot=resolved_bot,
        )

    async def on_ready(self):
        print(f"Elite Dangerous Tools is ready!, {self.bot.user.name}")

    async def ping(self, ctx):
        await ctx.send("Pong")

    async def _resolve(self, value):
        if inspect.isawaitable(value):
            return await value
        return value

    async def system_info(self, ctx, arg):
        print(f"Received argument: {arg}")
        system_info = await self._resolve(self.ed_route.get_system_info(arg))
        await ctx.send(f"{arg}: {system_info}")

    async def path(self, ctx, initial_system_name, destination_system_name):
        await ctx.send(
            f"Calculate Path between {initial_system_name} and {destination_system_name}...  This may take a while"
        )
        route = await self._resolve(
            self.ed_route.path(initial_system_name, destination_system_name)
        )
        route_message = " → ".join(route)
        message = f"Route from {initial_system_name} to {destination_system_name}: {route_message} "
        await ctx.send(message)

    def chunked_system_list(self, system_list, size=5):
        for i in range(0, len(system_list), size):
            yield system_list[i : i + size]

    async def dump_system_cache_names(self, ctx):
        await ctx.send("Fetching all system names in cache... This may take a while")
        system_names = await self._resolve(self.ed_route.get_all_system_names())
        for chunk in self.chunked_system_list(system_names, size=10):
            system_names_message = ", ".join(chunk)
            await ctx.send(f"Systems in cache: {system_names_message}")
        await ctx.send(f"Total number of systems in cache: {len(system_names)}")

    def register_commands(self):
        # ``discord.ext.commands`` expects plain callables whose first
        # parameter is ``ctx`` (plus any user arguments).  Using a bound
        # method would insert ``self`` as the first argument, causing
        # the framework to complain about the signature.  To keep the
        # instance methods while satisfying the API we register small
        # wrappers that delegate back to ``self``.

        @self.bot.command()
        async def ping(ctx):
            return await self.ping(ctx)

        @self.bot.command()
        async def system_info(ctx, arg):
            return await self.system_info(ctx, arg)

        @self.bot.command()
        async def path(ctx, initial_system_name, destination_system_name):
            return await self.path(ctx, initial_system_name, destination_system_name)

        @self.bot.command()
        async def dump_system_cache_names(ctx):
            return await self.dump_system_cache_names(ctx)

    def run(self):
        """Start the bot using the configured token/logging.

        This call is intentionally side‑effecty, so tests in which we don't
        want to connect to Discord shouldn't use it.
        """
        self.bot.run(self.token, log_handler=self.log_handler, log_level=self.log_level)
