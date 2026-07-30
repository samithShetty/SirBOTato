"""Application entry point for SirBOTato."""

import logging

from src.config import Settings
from src.discord_bot import create_discord_client


def main() -> None:
    settings = Settings.from_environment()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    create_discord_client(settings).run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
