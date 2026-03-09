from discord_bot import DiscordBot
from loguru import logger
from logging_utils import setup_logging

"""Launch script for the Discord bot process."""


def main() -> None:
    logger.info("Starting Discord runner")
    try:
        bot = DiscordBot.create_from_env()
        logger.debug("DiscordBot instance created")
        bot.run()
    except Exception:
        logger.exception("Discord runner failed")
        raise


if __name__ == "__main__":
    setup_logging()
    main()
