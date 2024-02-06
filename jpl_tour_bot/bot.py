"""Scrape the NASA JPL tours webpage."""


import logging

from jpl_tour_bot import Args
from jpl_tour_bot.state import State

LOGGER = logging.getLogger(__name__)


def run_bot(args: Args, state: State) -> None:
    """
    Scrape the NASA JPL tours webpage.

    :param args: The command line arguments.
    :param state: State of the JPL tours, from the previous script execution.
    """
    pass
