# Discord Bot Integration Tests

This document describes the integration testing setup for the Elite Danger Discord Bot using pytest and mocking.

## Overview

The integration tests verify that the Discord bot commands work correctly without requiring a live Discord connection. Instead of using dpytest (which has compatibility issues with Python 3.14), we use Python's built-in `unittest.mock` library to simulate Discord interactions.

## Test Structure

Tests are located in [tests/test_discord_bot_integration.py](../tests/test_discord_bot_integration.py) and cover:

- **Command Execution**: Each bot command is tested independently
- **Message Responses**: Verified that commands send the correct messages
- **Bot Configuration**: Intents, command prefix, and event registration
- **State Management**: Multiple sequential operations and list chunking

## How the Tests Work

### Mock Context

The tests create a mock Discord context using `unittest.mock.AsyncMock`:

```python
def create_mock_context():
    """Create a mock context object that simulates Discord message context."""
    ctx = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = MagicMock()
    ctx.guild = MagicMock()
    ctx.channel = MagicMock()
    return ctx
```

This simulates the `discord.ext.commands.Context` object that Discord provides during normal bot operation.

### Fake Route Module

Tests inject a `FakeRoute` class instead of the real `ed_route_async` module:

```python
class FakeRoute:
    async def get_system_info(self, name):
        return f"info-for-{name}"
    
    async def get_all_system_names(self):
        return ["Sol", "Alpha Centauri", "Proxima Centauri"]
    
    async def path(self, initial, dest):
        return [initial, dest]
```

This allows tests to run without database dependencies.

## Running the Tests

Run all integration tests:

```bash
pytest tests/test_discord_bot_integration.py -v
```

Run a specific test:

```bash
pytest tests/test_discord_bot_integration.py::test_ping_command -v
```

Run with coverage:

```bash
pytest tests/test_discord_bot_integration.py --cov=src --cov-report=term
```

## Test Coverage

The integration tests cover the following commands:

### `!ping`
- **Test**: `test_ping_command()`
- **Verifies**: Bot responds with "Pong"

### `!system_info <system_name>`
- **Tests**: 
  - `test_system_info_command()` - Sol system
  - `test_system_info_command_with_different_system()` - Alpha Centauri system
  - `test_multiple_system_queries()` - Sequential queries
- **Verifies**: System information is correctly formatted and returned

### `!path <source> <destination>`
- **Test**: `test_path_command()`
- **Verifies**: 
  - Acknowledgment message is sent first
  - Route calculation message is sent with correct format
  - Systems are properly formatted with arrow separator

### `!dump_system_cache_names`
- **Test**: `test_dump_system_cache_names_command()`
- **Verifies**:
  - Acknowledgment message is sent
  - System names are chunked correctly (10 per message)
  - Total count is correct

### Bot Configuration Tests

- `test_command_availability()` - All commands are registered
- `test_bot_ready_event()` - Event listeners are registered
- `test_bot_intents_configured()` - Required intents are enabled
- `test_command_prefix_correct()` - Command prefix is "!"
- `test_bot_instance_creation()` - Bot is properly instantiated
- `test_default_intents_configuration()` - Default intents include message_content
- `test_chunked_system_list()` - List chunking works correctly

## Adding New Tests

To add integration tests for new commands:

1. Create a test function decorated with `@pytest.mark.asyncio`
2. Use the `bot` fixture to get a bot instance
3. Create a mock context with `create_mock_context()`
4. Call the command method
5. Assert that `ctx.send` was called with expected messages

Example:

```python
@pytest.mark.asyncio
async def test_new_command(bot):
    """Test the new_command command."""
    ctx = create_mock_context()
    await bot.new_command(ctx, "arg1", "arg2")
    
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "expected text" in call_args
```

## Dependencies

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `discord.py` - Discord bot library
- `python-dotenv` - Environment variable loading

All are specified in [requirements.txt](../requirements.txt).
