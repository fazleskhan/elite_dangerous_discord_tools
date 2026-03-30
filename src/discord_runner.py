"""Launch script for the Discord bot process.

[README:DISCORD_PROCESS_ENTRYPOINT]
### Discord Process Entrypoint
Entrypoint: `python src/discord_runner.py`

Overview: Starts the standalone Discord bot process with environment/default
wiring via `EDDiscordBot.create()`.

Arguments and configuration:

* CLI arguments: none.
* Environment requirement: `DISCORD_TOKEN` must be configured.
* Command prefix: optional in composition; default `!`.
[/README]

[README:STARTING]
Run the Discord bot process via:

`python ./src/discord_runner.py`
[/README]
"""

from ed_discord_bot import EDDiscordBot
from loguru import logger
from ed_app_logging import configure_logging


def main() -> None:
    """Start the standalone Discord bot process.

    The runner builds the fully wired bot from environment-backed defaults and
    then hands control to Discord.py. Any startup failure is logged and
    re-raised so process supervisors can treat it as a hard failure.
    """
    logger.info("Starting Discord runner")
    try:
        # Build the fully wired bot from environment/default composition.
        bot = EDDiscordBot.create(logger=logger)
        logger.debug("EDDiscordBot instance created")
        bot.run()
    except Exception:
        logger.exception("Discord runner failed")
        raise


if __name__ == "__main__":
    configure_logging()
    main()
