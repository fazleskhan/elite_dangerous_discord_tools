import pytest
import logging
import discord
import re
import asyncio
from discord.ext import commands
from unittest.mock import MagicMock

from discord_bot import DiscordBot
from ed_logging_utils import EDLoggingUtils


def main(): ...


class MockContext:
    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)

    def retrieve_messages(self):
        return self.sent_messages


class FakeRoute:
    """Simplified stand‑in for route module behavior used in tests."""

    def __init__(self):
        self.last_path_args = None
        self.last_init_import_dir = None

    async def init_datasource(self, import_dir: str = "./init"):
        self.last_init_import_dir = import_dir

    async def get_system_info(self, name):
        # just echo the name with a suffix so assertions can match
        return f"info-for-{name}"

    async def get_all_system_names(self):
        return ["A", "B", "C"]

    async def calc_systems_distance(self, system_name_one, system_name_two):
        return 4.377120022057882

    async def path(
        self,
        initial,
        dest,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        self.last_path_args = (initial, dest, max_systems, min_distance, max_distance)
        # mimic the real return value used by tests
        return [initial, dest]

    async def bulk_load_cache(
        self,
        initial_system_names,
        max_nodes_visited,
        progress_callback=None,
    ):
        return initial_system_names[:max_nodes_visited]


@pytest.fixture
def bot():
    # each test gets its own bot instance wired to the fake route module
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot_instance = commands.Bot(command_prefix="!", intents=intents)
    return DiscordBot(
        ed_route_service=FakeRoute(),
        token="test-token",
        bot=bot_instance,
        logging_utils=EDLoggingUtils(),
    )


@pytest.mark.asyncio
async def test_ping(bot):
    ctx = MockContext()
    await bot.ping(ctx)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert re.match(r"^Pong \(\d+ ms\)$", sent_messages[0])


def test_constructor_raises_when_logging_utils_is_none():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot_instance = commands.Bot(command_prefix="!", intents=intents)

    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        DiscordBot(
            ed_route_service=FakeRoute(),
            token="test-token",
            bot=bot_instance,
            logging_utils=None,
        )


@pytest.mark.asyncio
async def test_system_info(bot):
    ctx = MockContext()
    arg = "Sol"
    await bot.system_info(ctx, arg)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert re.match(rf"^{arg}: info-for-{arg} \(\d+ ms\)$", sent_messages[0])


@pytest.mark.asyncio
async def test_system_info_when_payload_exceeds_2000_chars(bot):
    ctx = MockContext()
    arg = "Sol"
    long_payload = "x" * 2100

    async def long_system_info(name):
        return long_payload

    bot.ed_route.get_system_info = long_system_info
    await bot.system_info(ctx, arg)

    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 3
    assert all(len(message) <= 2000 for message in sent_messages[:-1])
    assert "".join(sent_messages[:-1]) == long_payload
    assert re.match(r"^Execution time: \d+ ms$", sent_messages[-1])


@pytest.mark.asyncio
async def test_path(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Alpha Centauri"
    max_system_count = 250
    await bot.path(ctx, source, dest, max_system_count)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        f"Calculate Path between {source} and {dest} with max system count {max_system_count} a min travel distance of 0 and a max travel distance of 10000...  This may take a while"
    )
    assert sent_messages[1].startswith(
        f"Route from {source} to {dest}: {source} → {dest}"
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])
    assert bot.ed_route.last_path_args == (source, dest, max_system_count, 0, 10000)


@pytest.mark.asyncio
async def test_path_with_optional_min_and_max_distance(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Alpha Centauri"
    max_system_count = 250
    min_distance = 5
    max_distance = 50

    await bot.path(
        ctx,
        source,
        dest,
        max_system_count,
        min_distance=min_distance,
        max_distance=max_distance,
    )
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert bot.ed_route.last_path_args == (
        source,
        dest,
        max_system_count,
        min_distance,
        max_distance,
    )


@pytest.mark.asyncio
async def test_path_when_route_is_none(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Beagle Point"
    max_system_count = 75

    async def no_route_path(
        initial,
        destination,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        return None

    bot.ed_route.path = no_route_path
    await bot.path(ctx, source, dest, max_system_count)

    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        f"Calculate Path between {source} and {dest} with max system count {max_system_count} a min travel distance of 0 and a max travel distance of 10000...  This may take a while"
    )
    assert sent_messages[1].startswith(
        f"No Path found between {source} and {dest} with max system count {max_system_count}"
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


@pytest.mark.asyncio
async def test_path_when_distance_is_less_than_min_distance(bot):
    ctx = MockContext()
    source = "TooClose"
    dest = "Target"

    async def filtered_path(
        initial,
        destination,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        distance = -1.0
        if min_distance <= distance <= max_distance:
            return [initial, destination]
        return None

    bot.ed_route.path = filtered_path
    await bot.path(ctx, source, dest, 100)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[1].startswith(
        f"No Path found between {source} and {dest} with max system count 100"
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


@pytest.mark.asyncio
async def test_path_when_distance_is_greater_than_max_distance(bot):
    ctx = MockContext()
    source = "TooFar"
    dest = "Target"

    async def filtered_path(
        initial,
        destination,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        distance = 20001.0
        if min_distance <= distance <= max_distance:
            return [initial, destination]
        return None

    bot.ed_route.path = filtered_path
    await bot.path(ctx, source, dest, 100)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[1].startswith(
        f"No Path found between {source} and {dest} with max system count 100"
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


@pytest.mark.asyncio
async def test_path_when_distance_is_between_min_and_max_distance(bot):
    ctx = MockContext()
    source = "InRange"
    dest = "Target"

    async def filtered_path(
        initial,
        destination,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        distance = 42.0
        if min_distance <= distance <= max_distance:
            return [initial, destination]
        return None

    bot.ed_route.path = filtered_path
    await bot.path(ctx, source, dest, 100)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[1].startswith(
        f"Route from {source} to {dest}: {source} → {dest}"
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


@pytest.mark.asyncio
async def test_path_emits_progress_callback_messages(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Sirius"
    progress_message = "Analyzed 30 of 100 systems"

    async def path_with_progress(
        initial,
        destination,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        if progress_callback is not None:
            progress_callback(progress_message)
        return [initial, destination]

    bot.ed_route.path = path_with_progress
    await bot.path(ctx, source, dest, 100)
    await asyncio.sleep(0.01)

    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) >= 3
    assert any(message == progress_message for message in sent_messages)
    assert any(
        message.startswith(
            f"Calculate Path between {source} and {dest} with max system count 100"
        )
        for message in sent_messages
    )
    assert any(
        message.startswith(f"Route from {source} to {dest}: {source} → {dest}")
        for message in sent_messages
    )


@pytest.mark.asyncio
async def test_calc_systems_distance(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Alpha Centauri"
    await bot.calc_systems_distance(ctx, source, dest)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert re.match(
        rf"^Distance between {source} and {dest}: 4\.377120022057882 \(\d+ ms\)$",
        sent_messages[0],
    )


@pytest.mark.asyncio
async def test_dump_system_cache_names(bot):
    ctx = MockContext()
    await bot.dump_system_cache_names(ctx)
    sent_messages = ctx.retrieve_messages()
    assert (
        sent_messages[0]
        == "Fetching all system names in cache... This may take a while"
    )
    # middle messages should start with the expected prefix and derive from FakeRoute
    assert sent_messages[1].startswith("Systems in cache:")
    assert re.match(
        r"^Total number of systems in cache: 3 \(\d+ ms\)$", sent_messages[-1]
    )


@pytest.mark.asyncio
async def test_init_datasource_command(bot):
    ctx = MockContext()
    await bot.init_datasource(ctx, "./custom-init")
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert re.match(
        r"^Datasource initialized from \./custom-init \(\d+ ms\)$", sent_messages[0]
    )
    assert bot.ed_route.last_init_import_dir == "./custom-init"


@pytest.mark.asyncio
async def test_bulk_load_cache_command(bot, monkeypatch):
    ctx = MockContext()
    captured = {"initial_system_names": None, "max_nodes_visited": None}

    async def fake_bulk_load_cache(
        initial_system_names, max_nodes_visited, progress_callback=None
    ):
        return captured.update(
            {
                "initial_system_names": initial_system_names,
                "max_nodes_visited": max_nodes_visited,
            }
        ) or ["Sol", "Alpha Centauri"]

    monkeypatch.setattr(bot.ed_route, "bulk_load_cache", fake_bulk_load_cache)

    await bot.bulk_load_cache(ctx, "Sol,Alpha Centauri", 50)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        "Bulk loading cache from seeds ['Sol', 'Alpha Centauri'] with max_nodes_visited=50"
    )
    assert sent_messages[1].startswith("Bulk load complete. Loaded 2 systems")
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])
    assert captured["initial_system_names"] == ["Sol", "Alpha Centauri"]
    assert captured["max_nodes_visited"] == 50


if __name__ == "__main__":
    main()
