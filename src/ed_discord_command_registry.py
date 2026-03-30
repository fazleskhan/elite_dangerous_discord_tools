from __future__ import annotations

from typing import Any

from ed_constants import default_init_dir
from ed_protocols import DiscordBotProtocol, DiscordContextProtocol


def register_discord_commands(bot: DiscordBotProtocol, handlers: Any) -> None:
    """Register the project's Discord command surface on a bot instance.

    The registry keeps Discord.py declaration boilerplate out of `EDDiscordBot`
    by binding the expected command names and signatures to methods on the
    supplied handler object.
    """

    @bot.command()
    async def ping(ctx: DiscordContextProtocol) -> None:
        await handlers.ping(ctx)

    @bot.command()
    async def system_info(ctx: DiscordContextProtocol, arg: str) -> None:
        await handlers.system_info(ctx, arg)

    @bot.command()
    async def path(
        ctx: DiscordContextProtocol,
        initial_system_name: str,
        destination_system_name: str,
        max_system_count: int = 100,
        min_distance: int = 0,
        max_distance: int = 10000,
    ) -> None:
        await handlers.path(
            ctx,
            initial_system_name,
            destination_system_name,
            max_system_count,
            min_distance,
            max_distance,
        )

    @bot.command()
    async def calc_systems_distance(
        ctx: DiscordContextProtocol, system_name_one: str, system_name_two: str
    ) -> None:
        await handlers.calc_systems_distance(ctx, system_name_one, system_name_two)

    @bot.command()
    async def dump_system_cache_names(ctx: DiscordContextProtocol) -> None:
        await handlers.dump_system_cache_names(ctx)

    @bot.command()
    async def init_datasource(
        ctx: DiscordContextProtocol, import_dir: str = default_init_dir
    ) -> None:
        await handlers.init_datasource(ctx, import_dir)

    @bot.command()
    async def bulk_load_cache(
        ctx: DiscordContextProtocol, initial_systems: str, max_nodes_visited: int
    ) -> None:
        await handlers.bulk_load_cache(ctx, initial_systems, max_nodes_visited)
