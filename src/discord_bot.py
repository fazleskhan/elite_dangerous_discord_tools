import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import ed_route_async

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
log_location = os.getenv("LOG_LOCATION", "discord_bot.log")

handler = logging.FileHandler(filename=log_location, encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)



@bot.event
async def on_ready():
    print(f"Elite Dangerous Tools is ready!, {bot.user.name}")



# !ping command
@bot.command()
async def ping(ctx):
    await ctx.send("Pong")


# !system_info command
@bot.command()
async def system_info(ctx, arg):
    print(f"Received argument: {arg}")

    system_info = await ed_route_async.get_system_info(arg)
    await ctx.send(f"{arg}: {system_info}")


# !path <initial> <destination>
@bot.command()
async def path(ctx, initial_system_name, destination_system_name):
    await ctx.send(
        f"Calculate Path between {initial_system_name} and {destination_system_name}...  This may take a while"
    )
    route = await ed_route_async.path(initial_system_name, destination_system_name)
    route_message = " → ".join(route)
    message = f"Route from {initial_system_name} to {destination_system_name}: {route_message} "
    await ctx.send(message)


def chunked_system_list(system_list, size=5):
    for i in range(0, len(system_list), size):
        yield system_list[i : i + size]


# !all_systems command
@bot.command()
async def dump_system_cache_names(ctx):
    await ctx.send("Fetching all system names in cache... This may take a while")
    system_names = await ed_route_async.get_all_system_names()
    for chunk in chunked_system_list(system_names, size=10):
        system_names_message = ", ".join(chunk)
        await ctx.send(f"Systems in cache: {system_names_message}")
    await ctx.send(f"Total number of systems in cache: {len(system_names)}")


# pulled bot.run() to avoid blocking the event loop during testing
# bot.run(token, log_handler=handler, log_level=logging.DEBUG)
