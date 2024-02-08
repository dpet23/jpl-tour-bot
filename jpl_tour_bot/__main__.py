"""Scrape the NASA JPL tours and notify if a reservation can be made."""

import logging
import sys

from jpl_tour_bot import STATE_FILE, Args
from jpl_tour_bot.bot import run_bot
from jpl_tour_bot.log_utils import StoreWarningsErrors
from jpl_tour_bot.state import State

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s',
)

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Entrypoint for the package."""
    notification_messages = []

    state = None
    with StoreWarningsErrors(logger='jpl_tour_bot', min_log_level=logging.WARNING) as handler:
        args = Args.parse_args()
        LOGGER.debug(args)

        state = State.from_file(STATE_FILE)
        LOGGER.debug(state)

        notification_messages = run_bot(args, state)
        # FUTURE: modify a copy of the `state`, and write back tour msg/avail only after notification sent

    if not handler.errors and not handler.warnings:
        LOGGER.info('Bot finished successfully')

    # send notification if necessary
    print(f'{notification_messages = }\n\n{handler.warnings = }\n\n{handler.errors = }')

    if state is not None:
        state.save_to_file(STATE_FILE)

    if handler.errors:
        sys.exit(1)
    if handler.warnings:
        sys.exit(2)


if __name__ == '__main__':
    main()
