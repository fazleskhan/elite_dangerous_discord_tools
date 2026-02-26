import discord_bot
import pytest


def main(): ...


class MockContext:
    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)

    def retrieve_messages(self):
        return self.sent_messages

@pytest.mark.asyncio
async def test_ping():

    ctx = MockContext()

    await discord_bot.ping_edt(ctx)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert sent_messages[0] == "Pong"


@pytest.mark.asyncio
async def test_system_info():

    ctx = MockContext()

    arg = "Sol"
    await discord_bot.system_info(ctx, arg)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 1
    assert sent_messages[0].startswith(f"{arg}: ")


@pytest.mark.asyncio
async def test_path():

    ctx = MockContext()

    source_system_name = "Sol"
    destination_system_name = "Alpha Centauri"
    await discord_bot.path(ctx, source_system_name, destination_system_name)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) == 2
    assert sent_messages[0].startswith(
        f"Calculate Path between {source_system_name} and {destination_system_name}...  This may take a while"
    )
    assert sent_messages[1].startswith(
        f"Route from {source_system_name} to {destination_system_name}: {source_system_name} → {destination_system_name}"
    )


@pytest.mark.asyncio
async def test_dump_system_cache_names():

    ctx = MockContext()

    await discord_bot.dump_system_cache_names(ctx)
    sent_messages = ctx.retrieve_messages()
    assert len(sent_messages) > 1
    assert (
        sent_messages[0]
        == "Fetching all system names in cache... This may take a while"
    )
    for message in sent_messages[1:-1]:
        assert isinstance(message, str)
        assert len(message) > 0
        assert message.startswith("Systems in cache:")
    assert sent_messages[-1].startswith("Total number of systems in cache: ")


if __name__ == "__main__":
    main()
