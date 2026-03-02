import logging
from dotenv import load_dotenv
from discord_bot import DiscordBot


def main():
    load_dotenv()
    bot = DiscordBot.create()
    bot.run()


if __name__ == "__main__":
    main()
