from discord_bot import DiscordBot

"""Launch script for the Discord bot process."""


def main() -> None:
    bot = DiscordBot.create()
    bot.run()


if __name__ == "__main__":
    main()
