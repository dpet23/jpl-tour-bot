"""Scrape the NASA JPL tours webpage."""


import logging
import sys

from jpl_tour_bot import Args
from jpl_tour_bot.browser import ChromeWebDriver
from jpl_tour_bot.state import State

LOGGER = logging.getLogger(__name__)


def run_bot(args: Args, state: State) -> None:
    """
    Scrape the NASA JPL tours webpage.

    :param args: The command line arguments.
    :param state: State of the JPL tours, from the previous script execution.
    """
    browser = ChromeWebDriver.start_new_session(executable_path=args.browser_binary, headless=not args.ui)

    # Ensure we're running in a new session.
    browser_session_id: str = browser.session_id or ''
    if browser_session_id == state.BROWSER_SESSION:
        LOGGER.error('The session ID has not changed from the saved state. Aborting.')
        browser.shut_down()
        sys.exit(1)
    state.BROWSER_SESSION = browser_session_id

    temp(browser, args.ui)

    browser.shut_down()


def temp(browser: ChromeWebDriver, ui: bool) -> None:
    browser.get('https://www.google.com')
    LOGGER.info(browser.title)

    if ui:
        import time

        time.sleep(10)
