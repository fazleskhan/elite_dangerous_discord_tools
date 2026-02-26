#from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import discord_bot


def main(): ...

bot = discord_bot.bot
handler = discord_bot.handler
token = discord_bot.token


bot.run(token, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
