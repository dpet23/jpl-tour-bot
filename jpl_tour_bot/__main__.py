"""Scrape the NASA JPL tours and notify if a reservation can be made."""

import logging
import sys

from jpl_tour_bot import STATE_FILE, Args
from jpl_tour_bot.bot import run_bot
from jpl_tour_bot.state import State

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s',
)

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Entrypoint for the package."""
    args = Args.parse_args()
    LOGGER.debug(args)

    state = State.from_file(STATE_FILE)
    LOGGER.debug(state)

    try:
        run_bot(args, state)
    except Exception:
        LOGGER.exception('Top-level failure')
        sys.exit(1)
    else:
        LOGGER.info('Finished successfully')
    finally:
        state.save_to_file(STATE_FILE)

        # send notification if necessary


if __name__ == '__main__':
    main()
