import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
import ed_route
import factory
import ed_route_async
import time

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
secret_role = "Gamer"


@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")


@bot.event
async def on_member_join(member):
    await member.sent(f"Welcome to the server {member.name}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "shit" in message.content.lower():
        await message.delete()
        await message.channel.send(f"{message.author.mention} don't use that word")

    await bot.process_commands(message)


# !hello command
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")


@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secret_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(
            f"{ctx.author.mention} you have been assigned the {secret_role} role"
        )
    else:
        await ctx.send("Role doesn't exist")


@bot.command()
async def remove(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secret_role)
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send(
            f"{ctx.author.mention} you have been removed from the {secret_role} role"
        )
    else:
        await ctx.send("Role doesn't exist")


@bot.command()
async def dm(ctx, *, msg):
    await ctx.author.send(f"You said {msg}")


@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message!")


@bot.command()
@commands.has_role(secret_role)
async def secret(ctx):
    await ctx.send(f"Welcome to the club!")


@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")


@secret.error
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You don't have permission to use this command!")


# !system_info command
@bot.command()
async def system_info(ctx, arg):
    print(f"Received argument: {arg}")

    system_info = await ed_route_async.get_system_info(arg)
    await ctx.send(f"{arg}: {system_info}")


@bot.command()
async def sleep(ctx):
    message = "first message"
    await ctx.send(message)
    time.sleep(30)  # Pauses for 3 seconds
    message = "second message"
    await ctx.send(message)


# !path <initial> <destination>
@bot.command()
async def path(ctx, initial_system_name, destination_system_name):
    await ctx.send(
        f"Calculate Path between {initial_system_name} and {destination_system_name}...  This may take a while"
    )
    route = await ed_route_async.path(initial_system_name, destination_system_name)
    route_message = " → ".join(route)
    await ctx.send(
        f"Route from {initial_system_name} to {destination_system_name}: {route_message} "
    )


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


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
