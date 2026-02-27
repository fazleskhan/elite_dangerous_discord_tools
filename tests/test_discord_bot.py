import pytest

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
    """Simplified stand‑in for ``ed_route_async`` used in tests."""

    async def get_system_info(self, name):
        # just echo the name with a suffix so assertions can match
        return f"info-for-{name}"

    async def get_all_system_names(self):
        return ["A", "B", "C"]

    async def path(self, initial, dest):
        # mimic the real return value used by tests
        return [initial, dest]


@pytest.fixture
def bot():
    # each test gets its own bot instance wired to the fake route module
    return DiscordBot(ed_route_module=FakeRoute())


@pytest.mark.asyncio
async def test_ping(bot):
    ctx = MockContext()
    await bot.ping(ctx)
    sent_messages = ctx.retrieve_messages()
    assert sent_messages == ["Pong"]


@pytest.mark.asyncio
async def test_system_info(bot):
    ctx = MockContext()
    arg = "Sol"
    await bot.system_info(ctx, arg)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert sent_messages[0] == f"{arg}: info-for-{arg}"


@pytest.mark.asyncio
async def test_path(bot):
    ctx = MockContext()
    source = "Sol"
    dest = "Alpha Centauri"
    await bot.path(ctx, source, dest)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        f"Calculate Path between {source} and {dest}...  This may take a while"
    )
    assert sent_messages[1].startswith(
        f"Route from {source} to {dest}: {source} → {dest}"
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
    assert sent_messages[-1].startswith("Total number of systems in cache: ")


if __name__ == "__main__":
    main()
