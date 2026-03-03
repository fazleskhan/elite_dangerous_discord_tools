from discord_bot import DiscordBot


def main() -> None:
    bot = DiscordBot.create()
    bot.run()


if __name__ == "__main__":
    main()
