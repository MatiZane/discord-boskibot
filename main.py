from __future__ import annotations

import logging
import sys

from miku_bot.bot import MikuBot
from miku_bot.config import load_config


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()
    if not config.discord_token:
        logging.error(
            "Brak DISCORD_TOKEN w pliku .env! Skopiuj .env.example do .env i wpisz token bota z Discord Developer Portal."
        )
        return 1

    bot = MikuBot(config)
    bot.run(config.discord_token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
