"""Integration tests for DiscordBot using mock Discord objects.

Tests the bot's command handlers by simulating Discord interactions without
requiring a live Discord connection. Creates mock guilds, channels, and users
to test command execution and message responses.
"""

import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch

from discord_bot import DiscordBot


class FakeRoute:
    """Simplified stand-in for route module behavior used in tests."""

    async def get_system_info(self, name):
        return f"info-for-{name}"

    async def get_all_system_names(self):
        return ["Sol", "Alpha Centauri", "Proxima Centauri"]

    async def path(self, initial, dest):
        return [initial, dest]


def create_mock_context():
    """Create a mock context object that simulates Discord message context."""
    ctx = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = MagicMock()
    ctx.author.name = "TestUser"
    ctx.guild = MagicMock()
    ctx.guild.id = 12345
    ctx.channel = MagicMock()
    ctx.channel.id = 67890
    return ctx


@pytest.fixture
def bot():
    """Create a bot instance with fake route for integration testing."""
    return DiscordBot(
        ed_route_module=FakeRoute(),
        command_prefix="!",
    )


@pytest.mark.asyncio
async def test_ping_command(bot):
    """Test that the ping command responds with 'Pong'."""
    ctx = create_mock_context()
    await bot.ping(ctx)
    ctx.send.assert_called_once_with("Pong")


@pytest.mark.asyncio
async def test_system_info_command(bot):
    """Test the system_info command returns system information."""
    ctx = create_mock_context()
    await bot.system_info(ctx, "Sol")
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Sol" in call_args
    assert "info-for-Sol" in call_args


@pytest.mark.asyncio
async def test_system_info_command_with_different_system(bot):
    """Test system_info with different system names."""
    ctx = create_mock_context()
    await bot.system_info(ctx, "Alpha Centauri")
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Alpha Centauri" in call_args
    assert "info-for-Alpha Centauri" in call_args


@pytest.mark.asyncio
async def test_path_command(bot):
    """Test the path command calculates route between systems."""
    ctx = create_mock_context()
    await bot.path(ctx, "Sol", "Andromeda")

    # Should have been called twice: once for acknowledgment, once for route
    assert ctx.send.call_count == 2

    # First call: acknowledgment
    first_call = ctx.send.call_args_list[0][0][0]
    assert "Calculate Path" in first_call
    assert "Sol" in first_call
    assert "Andromeda" in first_call

    # Second call: the actual route
    second_call = ctx.send.call_args_list[1][0][0]
    assert "Route from Sol to Andromeda" in second_call
    assert "Sol → Andromeda" in second_call


@pytest.mark.asyncio
async def test_dump_system_cache_names_command(bot):
    """Test dump_system_cache_names lists all systems in cache."""
    ctx = create_mock_context()
    await bot.dump_system_cache_names(ctx)

    # Should have been called multiple times
    assert ctx.send.call_count >= 3  # acknowledgment + systems + total

    # First call: acknowledgment
    first_call = ctx.send.call_args_list[0][0][0]
    assert "Fetching all system names in cache" in first_call

    # Middle call(s): system lists
    second_call = ctx.send.call_args_list[1][0][0]
    assert "Systems in cache:" in second_call

    # Last call: total count
    last_call = ctx.send.call_args_list[-1][0][0]
    assert "Total number of systems in cache:" in last_call
    assert "3" in last_call


@pytest.mark.asyncio
async def test_command_availability(bot):
    """Test that commands are available and properly registered."""
    commands_dict = {cmd.name: cmd for cmd in bot.bot.commands}

    assert "ping" in commands_dict
    assert "system_info" in commands_dict
    assert "path" in commands_dict
    assert "dump_system_cache_names" in commands_dict


def test_bot_ready_event(bot):
    """Test that on_ready event is properly registered."""
    # Verify that the on_ready event is registered
    assert bot.bot._listeners is not None


@pytest.mark.asyncio
async def test_bot_intents_configured(bot):
    """Verify that bot is configured with required intents."""
    assert bot.bot.intents.message_content is True
    assert bot.bot.intents.members is True


def test_command_prefix_correct(bot):
    """Verify that the bot uses the expected command prefix."""
    assert bot.bot.command_prefix == "!"


def test_bot_instance_creation(bot):
    """Test that bot instance is properly created."""
    assert bot.bot is not None
    assert isinstance(bot.bot, commands.Bot)
    assert bot.ed_route is not None


@pytest.mark.asyncio
async def test_multiple_system_queries(bot):
    """Test sequential system info queries."""
    systems = ["Sol", "Alpha Centauri", "Sirius"]

    for system in systems:
        ctx = create_mock_context()
        await bot.system_info(ctx, system)
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert system in call_args
        assert f"info-for-{system}" in call_args


@pytest.mark.asyncio
async def test_chunked_system_list(bot):
    """Test that system list chunking works correctly."""
    systems = list(range(1, 26))  # 25 systems
    chunks = list(bot.chunked_system_list(systems, size=10))

    assert len(chunks) == 3
    assert len(chunks[0]) == 10
    assert len(chunks[1]) == 10
    assert len(chunks[2]) == 5


def test_default_intents_configuration():
    """Test that default intents are properly configured."""
    bot = DiscordBot(ed_route_module=FakeRoute())

    assert bot.bot.intents.message_content is True
    assert bot.bot.intents.members is True
    assert bot.bot.intents.default() is not None
