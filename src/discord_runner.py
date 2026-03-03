import logging
from discord_bot import DiscordBot
from logging_utils import resolve_log_level

"""Launch script for the Discord bot process."""

logger = logging.getLogger(__name__)


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
    logging.basicConfig(level=resolve_log_level(logging.INFO))
    main()
