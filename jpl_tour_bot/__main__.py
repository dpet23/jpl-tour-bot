"""Scrape the NASA JPL tours and notify if a reservation can be made."""

import logging
import sys

from jpl_tour_bot import STATE_FILE, Args
from jpl_tour_bot.bot import run_bot
from jpl_tour_bot.log_utils import StoreWarningsErrors
from jpl_tour_bot.notify_discord import post_discord
from jpl_tour_bot.state import State

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s',
)

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Entrypoint for the package."""
    notification_messages = []

    args = None
    state = None
    with StoreWarningsErrors(logger='jpl_tour_bot', min_log_level=logging.WARNING) as handler:
        args = Args.parse_args()
        LOGGER.info(args)

        state = State.from_file(STATE_FILE)
        LOGGER.debug(state)

        notification_messages = run_bot(args, state)

    if not handler.errors and not handler.warnings:
        LOGGER.info('Bot finished successfully')

    # Send Discord notification if necessary.
    if (notification_messages or handler.warnings or handler.errors) and (args is not None and args.notify):
        post_discord(args.notify, notification_messages, handler.warnings, handler.errors)
    else:
        LOGGER.info('Nothing to post')

    # Save the updated state back to the file.
    if state is not None:
        state.save_to_file(STATE_FILE)

    if handler.errors:
        sys.exit(1)
    if handler.warnings:
        sys.exit(2)


if __name__ == '__main__':
    main()
