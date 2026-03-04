import pytest
import logging
import discord
import re
from discord.ext import commands
from unittest.mock import MagicMock

from discord_bot import DiscordBot


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

    async def get_system_info(self, name):
        # just echo the name with a suffix so assertions can match
        return f"info-for-{name}"

    async def get_all_system_names(self):
        return ["A", "B", "C"]

    async def calc_systems_distance(self, system_name_one, system_name_two):
        return 4.377120022057882

    async def path(
        self, initial, dest, max_systems=100, min_distance=0, max_distance=10000
    ):
        self.last_path_args = (initial, dest, max_systems, min_distance, max_distance)
        # mimic the real return value used by tests
        return [initial, dest]


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
        log_location="logs/discord_bot.log",
        log_level=logging.DEBUG,
        log_handler=MagicMock(),
        bot=bot_instance,
    )


@pytest.mark.asyncio
async def test_ping(bot):
    ctx = MockContext()
    await bot.ping(ctx)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert re.match(r"^Pong \(\d+ ms\)$", sent_messages[0])


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
        initial, destination, max_systems=100, min_distance=0, max_distance=10000
    ):
        return None

    bot.ed_route.path = no_route_path
    await bot.path(ctx, source, dest, max_system_count)

    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        f"Calculate Path between {source} and {dest} with max system count {max_system_count} a min travel distance of 0 and a max travel distance of 10000...  This may take a while"
    )
    assert (
        sent_messages[1].startswith(
            f"No Path found between {source} and {dest} with max system count {max_system_count}"
        )
    )
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


@pytest.mark.asyncio
async def test_path_when_distance_is_less_than_min_distance(bot):
    ctx = MockContext()
    source = "TooClose"
    dest = "Target"

    async def filtered_path(
        initial, destination, max_systems=100, min_distance=0, max_distance=10000
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
        initial, destination, max_systems=100, min_distance=0, max_distance=10000
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
        initial, destination, max_systems=100, min_distance=0, max_distance=10000
    ):
        distance = 42.0
        if min_distance <= distance <= max_distance:
            return [initial, destination]
        return None

    bot.ed_route.path = filtered_path
    await bot.path(ctx, source, dest, 100)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[1].startswith(f"Route from {source} to {dest}: {source} → {dest}")
    assert re.search(r"\(\d+ ms\)$", sent_messages[1])


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
    assert re.match(r"^Total number of systems in cache: 3 \(\d+ ms\)$", sent_messages[-1])


if __name__ == "__main__":
    main()
