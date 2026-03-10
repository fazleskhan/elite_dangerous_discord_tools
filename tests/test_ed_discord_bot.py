import asyncio
import concurrent.futures
import re
from typing import Any

import pytest

import ed_discord_bot
from tests.helpers import ThreadSafeLogger


class FakeContext:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class FakeBot:
    def __init__(self, command_prefix: str = "!") -> None:
        self.command_prefix = command_prefix
        self.user = type("User", (), {"name": "TestBot"})()
        self.commands: dict[str, Any] = {}
        self.events: list[Any] = []
        self.run_args: tuple[Any, ...] | None = None

    def event(self, fn):  # type: ignore[no-untyped-def]
        self.events.append(fn)
        return fn

    def command(self, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        def decorator(fn):  # type: ignore[no-untyped-def]
            self.commands[fn.__name__] = fn
            return fn

        return decorator

    def run(self, *args: Any, **kwargs: Any) -> None:
        self.run_args = args


class FakeRouteService:
    def __init__(self) -> None:
        self.last_path_args: tuple[Any, ...] | None = None
        self.last_init_import_dir: str | None = None
        self.last_bulk_args: tuple[list[str], int] | None = None

    def get_system_info(self, system_name: str) -> dict[str, Any]:
        return {"name": system_name}

    def get_all_system_names(self) -> list[str]:
        return [f"System-{index}" for index in range(25)]

    def calc_systems_distance(self, one: str, two: str) -> float:
        return 4.37

    async def path(
        self,
        initial_system_name: str,
        destination_system_name: str,
        max_systems: int = 100,
        min_distance: int = 0,
        max_distance: int = 10000,
        progress_callback=None,  # type: ignore[no-untyped-def]
    ) -> list[str]:
        self.last_path_args = (
            initial_system_name,
            destination_system_name,
            max_systems,
            min_distance,
            max_distance,
        )
        if progress_callback is not None:
            progress_callback("halfway")
        return [initial_system_name, destination_system_name]

    async def init_datasource(self, import_dir: str = "./init") -> None:
        self.last_init_import_dir = import_dir

    async def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback=None,  # type: ignore[no-untyped-def]
    ) -> list[str]:
        self.last_bulk_args = (initial_system_names, max_nodes_visited)
        if progress_callback is not None:
            progress_callback("loaded")
        return initial_system_names[:max_nodes_visited]


@pytest.fixture()
def logger() -> ThreadSafeLogger:
    return ThreadSafeLogger()


@pytest.fixture()
def discord_bot(logger: ThreadSafeLogger) -> ed_discord_bot.EDDiscordBot:
    return ed_discord_bot.EDDiscordBot(
        ed_route_service=FakeRouteService(),
        token="token",
        bot=FakeBot(),
        logging_utils=logger,
    )


def test_discord_bot_validates_dependencies(logger: ThreadSafeLogger) -> None:
    route = FakeRouteService()
    bot = FakeBot()
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        ed_discord_bot.EDDiscordBot(route, "token", bot, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ed_route_service of type RouteServiceProtocol is required"):
        ed_discord_bot.EDDiscordBot(None, "token", bot, logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="token of type str is required"):
        ed_discord_bot.EDDiscordBot(route, None, bot, logger)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bot of type commands.Bot is required"):
        ed_discord_bot.EDDiscordBot(route, "token", None, logger)  # type: ignore[arg-type]


def test_default_intents_enable_required_flags() -> None:
    intents = ed_discord_bot.EDDiscordBot._default_intents()
    assert intents.message_content is True
    assert intents.members is True


def test_create_uses_injected_route_and_bot(monkeypatch: pytest.MonkeyPatch, logger: ThreadSafeLogger) -> None:
    route = FakeRouteService()
    bot = FakeBot("?")
    monkeypatch.setattr(ed_discord_bot, "load_dotenv", lambda: None)
    created = ed_discord_bot.EDDiscordBot.create(
        route_service=route, logging_utils=logger, token="token", bot=bot
    )
    assert created.ed_route is route
    assert created.bot is bot


def test_create_builds_default_dependencies(monkeypatch: pytest.MonkeyPatch, logger: ThreadSafeLogger) -> None:
    route = FakeRouteService()
    datasource = object()
    cache = object()
    monkeypatch.setattr(ed_discord_bot, "load_dotenv", lambda: None)
    monkeypatch.setattr(ed_discord_bot.ed_datasource_factory, "create_datasource", lambda: datasource)
    monkeypatch.setattr(ed_discord_bot.EDGis, "create", staticmethod(lambda logging_utils: type("GIS", (), {"fetch_system_info": lambda self, name: {"name": name}, "fetch_neighbors": lambda self, x, y, z: []})()))
    monkeypatch.setattr(ed_discord_bot.edgis_cache.EDGisCache, "create", staticmethod(lambda datasource, logging_utils, fetch_system_info_fn, fetch_neighbors_fn: cache))
    monkeypatch.setattr(ed_discord_bot.EDRouteServiceFactory, "create", staticmethod(lambda datasource=None, cache=None, logging_utils=None: route))
    monkeypatch.setattr(ed_discord_bot.commands, "Bot", lambda command_prefix, intents: FakeBot(command_prefix))

    created = ed_discord_bot.EDDiscordBot.create(logging_utils=logger, token="token")

    assert created.ed_route is route
    assert created.bot.command_prefix == "!"


@pytest.mark.asyncio
async def test_on_ready_ping_and_resolve(discord_bot: ed_discord_bot.EDDiscordBot, logger: ThreadSafeLogger) -> None:
    await discord_bot.on_ready()
    ctx = FakeContext()
    await discord_bot.ping(ctx)
    assert logger.messages("info")
    assert re.match(r"^Pong \(\d+ ms\)$", ctx.messages[0])
    assert await discord_bot._resolve("value") == "value"
    assert await discord_bot._resolve(asyncio.sleep(0, result="async")) == "async"


@pytest.mark.asyncio
async def test_system_info_short_and_long_payloads(discord_bot: ed_discord_bot.EDDiscordBot) -> None:
    ctx = FakeContext()
    await discord_bot.system_info(ctx, "Sol")
    assert "Sol: {'name': 'Sol'}" in ctx.messages[0]

    async def long_info(_arg: str) -> str:
        return "x" * 4100

    discord_bot.ed_route.get_system_info = long_info  # type: ignore[method-assign]
    long_ctx = FakeContext()
    await discord_bot.system_info(long_ctx, "Sol")
    assert len(long_ctx.messages) == 4
    assert all(len(message) <= 2000 for message in long_ctx.messages[:-1])
    assert re.match(r"^Execution time: \d+ ms$", long_ctx.messages[-1])


@pytest.mark.asyncio
async def test_calc_distance_path_cache_dump_init_and_bulk_load(
    discord_bot: ed_discord_bot.EDDiscordBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = FakeContext()
    await discord_bot.calc_systems_distance(ctx, "Sol", "Lave")
    assert "Distance between Sol and Lave: 4.37" in ctx.messages[0]

    scheduled: list[str] = []

    def fake_run_coroutine_threadsafe(coro, loop):  # type: ignore[no-untyped-def]
        future: concurrent.futures.Future[None] = concurrent.futures.Future()

        async def consume() -> None:
            await coro
            scheduled.append("sent")
            future.set_result(None)

        loop.create_task(consume())
        return future

    monkeypatch.setattr(ed_discord_bot.asyncio, "run_coroutine_threadsafe", fake_run_coroutine_threadsafe)

    path_ctx = FakeContext()
    await discord_bot.path(path_ctx, "Sol", "Lave", 10, 1, 20)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert path_ctx.messages[0].startswith("Calculate Path between Sol and Lave")
    assert any("Route from Sol to Lave: Sol → Lave" in message for message in path_ctx.messages)
    assert scheduled == ["sent"]

    async def no_route(*args: Any, **kwargs: Any) -> None:
        return None

    discord_bot.ed_route.path = no_route  # type: ignore[method-assign]
    no_route_ctx = FakeContext()
    await discord_bot.path(no_route_ctx, "Sol", "Lave")
    assert no_route_ctx.messages[-1].startswith("No Path found between Sol and Lave")

    dump_ctx = FakeContext()
    await discord_bot.dump_system_cache_names(dump_ctx)
    assert dump_ctx.messages[0].startswith("Fetching all system names in cache")
    assert dump_ctx.messages[-1].startswith("Total number of systems in cache: 25")

    init_ctx = FakeContext()
    await discord_bot.init_datasource(init_ctx, "./seed")
    assert init_ctx.messages[0].startswith("Datasource initialized from ./seed")

    bulk_ctx = FakeContext()
    await discord_bot.bulk_load_cache(bulk_ctx, "Sol, Lave", 2)
    assert bulk_ctx.messages[0].startswith("Bulk loading cache from seeds ['Sol', 'Lave']")
    assert bulk_ctx.messages[-1].startswith("Bulk load complete. Loaded 2 systems")


def test_chunked_system_list_register_commands_and_run(
    discord_bot: ed_discord_bot.EDDiscordBot,
) -> None:
    assert list(discord_bot.chunked_system_list(list(range(12)), size=5)) == [
        [0, 1, 2, 3, 4],
        [5, 6, 7, 8, 9],
        [10, 11],
    ]
    assert {
        "ping",
        "system_info",
        "path",
        "calc_systems_distance",
        "dump_system_cache_names",
        "init_datasource",
        "bulk_load_cache",
    } <= set(discord_bot.bot.commands)

    discord_bot.run()
    assert discord_bot.bot.run_args == ("token",)


def test_run_requires_token(logger: ThreadSafeLogger) -> None:
    bot = ed_discord_bot.EDDiscordBot(
        ed_route_service=FakeRouteService(),
        token="token",
        bot=FakeBot(),
        logging_utils=logger,
    )
    bot.token = None  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="DISCORD_TOKEN is not configured"):
        bot.run()


def test_ed_discord_bot_main_is_a_noop() -> None:
    assert ed_discord_bot.main() is None
