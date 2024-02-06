"""Scrape the NASA JPL tours and notify if a reservation can be made."""

import logging

from jpl_tour_bot import STATE_FILE, Args
from jpl_tour_bot.state import State

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s',
)


def main() -> None:
    """Entrypoint for the package."""
    args = Args.parse_args()
    logging.debug(args)

    state = State.from_file(STATE_FILE)
    logging.debug(state)


if __name__ == '__main__':
    main()
