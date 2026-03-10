from discord_bot import DiscordBot
from loguru import logger
from ed_logging_utils import EDLoggingUtils

"""Launch script for the Discord bot process."""


def main() -> None:
    logger.info("Starting Discord runner")
    try:
        bot = DiscordBot.create()
        logger.debug("DiscordBot instance created")
        bot.run()
    except Exception:
        logger.exception("Discord runner failed")
        raise


if __name__ == "__main__":
    EDLoggingUtils.create()
    main()
