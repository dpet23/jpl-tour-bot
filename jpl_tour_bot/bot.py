"""Scrape the NASA JPL tours webpage."""

from __future__ import annotations

import logging
import random
import time
from textwrap import indent
from typing import TYPE_CHECKING, NamedTuple

from markdown_strings import code_block  # type: ignore[import-untyped]
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from tabulate import tabulate

from jpl_tour_bot import SCREENSHOT_PATH, URL_JPL_TOUR, WAIT_TIME_LIMITS, Args
from jpl_tour_bot.browser import ChromeWebDriver

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

    from jpl_tour_bot.state import State

LOGGER = logging.getLogger(__name__)


class Notification(NamedTuple):
    """An important state change to report as a notification."""

    title: str
    content: str

    def __str__(self) -> str:
        """Represent the notification as a string."""
        return f"{self.title}\n{indent(self.content, '\t')}"


def run_bot(args: Args, state: State) -> list[Notification]:
    """
    Scrape the NASA JPL tours webpage.

    :param args: The command line arguments.
    :param state: State of the JPL tours, from the previous script execution.
    :return: A list of important state changes to include in a notification.
    """
    if args.no_wait:
        LOGGER.debug('Starting bot immediately')
    else:
        wait_time = random.randrange(**WAIT_TIME_LIMITS)
        LOGGER.info('Waiting %d minutes', wait_time / 60)
        time.sleep(wait_time)

    browser = ChromeWebDriver.start_new_session(executable_path=args.browser_binary, headless=not args.ui)

    # Ensure we're running in a new session.
    browser_session_id: str = browser.session_id or ''
    if browser_session_id == state.BROWSER_SESSION:
        browser.shut_down()
        raise ValueError('The session ID has not changed from the saved state. Aborting.')
    state.BROWSER_SESSION = browser_session_id

    try:
        return _scrape_tour(browser, state)
    finally:
        browser.shut_down()


def _scrape_tour(browser: ChromeWebDriver, state: State) -> list[Notification]:
    """
    Find whether any NASA JPL tours are available.

    :param browser: The open browser instance.
    :param state: State of the JPL tours. Will be updated with new values.
    :return: A list of important state changes to include in a notification.
    """
    # Open the webpage.
    browser.open_url(URL_JPL_TOUR)

    time.sleep(5)

    notification_messages: list[Notification] = []

    # Search for the date of the next tour release.
    next_tour_msg = _get_next_tour_release_date(browser)

    # Check if the next tour release date has changed.
    if next_tour_msg != state.NEXT_TOUR_MSG:
        notification = Notification('Next tour message has changed', next_tour_msg)
        notification_messages.append(notification)
        LOGGER.info(notification)

        state.NEXT_TOUR_MSG = next_tour_msg

    time.sleep(5)

    # Search for available tours.
    _submit_tour_search_form(browser, tour_type='Visitor Day Tour', tour_size=1)
    tour_availability_notifications = _get_tour_availability_after_search(browser)

    # Check if the tour availability has changed.
    tour_availability_msg = '\n'.join(notification.content for notification in tour_availability_notifications)
    if tour_availability_msg != state.TOUR_AVAILABLE:
        for notification in tour_availability_notifications:
            notification_messages.append(notification)
            LOGGER.info(notification)

        state.TOUR_AVAILABLE = tour_availability_msg

    time.sleep(5)

    return notification_messages


def _get_next_tour_release_date(browser: ChromeWebDriver) -> str:
    """
    Find the posted message for the date of the next tour release.

    :param browser: The open browser instance.
    :return: The message announcing the date of the next tour release, from the JPL website.
    """
    next_tour_msg = '(empty)'

    text_to_search = 'Next Tours Release Date'
    LOGGER.info('Searching for the %s', text_to_search.lower())
    msg_element = browser.find_by_xpath(f"//h1[text()='{text_to_search}']/following-sibling::div")
    if msg_element:
        next_tour_msg = msg_element.text
        LOGGER.debug('Found next tour message: "%s"', next_tour_msg)

    return next_tour_msg


def _submit_tour_search_form(browser: ChromeWebDriver, *, tour_type: str, tour_size: int) -> None:
    """
    Fill out and submit the web form, searching for available tours.

    :param browser: The open browser instance.
    :param tour_type: The type of tour to search for, must be one of the values from the web dropdown.
    :param tour_size: The number of visitors, must be one of the form's allowed values.
    """
    LOGGER.info('Finding the tour search form')
    text_to_search = 'Reserve Here'
    search_form_element = browser.find_by_xpath(f"//h1[text()='{text_to_search}']/following-sibling::div")
    if not search_form_element:
        raise NoSuchElementException('Could not find tour search form')

    LOGGER.info('Selecting the tour type: "%s"', tour_type)
    tour_type_select = browser.find_by_xpath("//select[@name='categoryId']", parent=search_form_element)
    if not tour_type_select:
        raise NoSuchElementException('Could not find tour type select box')
    Select(tour_type_select).select_by_visible_text(tour_type)

    time.sleep(1)

    LOGGER.info('Entering the number of visitors: %d', tour_size)
    tour_size_input = browser.find_by_xpath("//input[@name='groupSize']", parent=search_form_element)
    if not tour_size_input:
        raise NoSuchElementException('Could not find tour size input box')
    tour_size_input.send_keys(str(tour_size))

    time.sleep(1)

    LOGGER.info('Submitting the tour search form')
    submit_form_button = browser.find_by_xpath("//button[contains(@class, 'btn-submit')]", parent=search_form_element)
    if not submit_form_button:
        raise NoSuchElementException('Could not find submit button for the tour search form')
    if not submit_form_button.is_enabled():
        raise RuntimeError('Submit button for the tour search form is not enabled')
    try:
        submit_form_button.click()
    except Exception:
        raise RuntimeError("Can't click on %s", submit_form_button.get_attribute('outerHTML')) from None


def _get_tour_availability_after_search(browser: ChromeWebDriver) -> list[Notification]:
    """
    After searching for tours by submitting a form, check if there's any tours available.

    :param browser: The open browser instance.
    :return: The availability of the next tours, from the JPL website, as a list of notifications to report.
    """
    LOGGER.info('Waiting for the tour search to load')
    browser.wait_until_visible(By.XPATH, "//*[@id='primary_column']/div/table")
    time.sleep(5)

    LOGGER.info('Trying to find the error message')
    try:
        error_msg_element = browser.find_by_xpath_or_error(
            "//*[@id='primary_column']/div/div/label[contains(@class, 'err')]"
        )
    except NoSuchElementException:
        # No error element was found, so a tour may be available.
        # Use a custom exception handler to suppress the error message.
        error_msg_element = None

    notification_title_new_availability = 'Tour availability has changed'

    if error_msg_element:
        return [Notification(notification_title_new_availability, error_msg_element.text.strip())]

    LOGGER.info('Trying to find the number of available tours')
    tour_availability_msg = browser.find_by_class('tour_count')
    if not tour_availability_msg:
        return [Notification(notification_title_new_availability, 'No tours found.')]

    notifications = [Notification(notification_title_new_availability, tour_availability_msg.text.strip())]

    LOGGER.info('Parsing the table of available tours')
    available_tours_table = browser.find_by_class('available_tours')
    if available_tours_table:
        available_tour_details = _parse_available_tours_table(browser, available_tours_table)
        notifications.append(Notification('Tour details', available_tour_details))

    browser.save_screenshot_full_page(str(SCREENSHOT_PATH.absolute()))
    return notifications


def _parse_available_tours_table(browser: ChromeWebDriver, available_tours_table: WebElement) -> str:
    """
    Parse the HTML table of available tours, extracting the details.

    :param browser: The open browser instance.
    :param available_tours_table: Web element representing the table of available tours.
    :return: The details of available tours, as a multiline string representing a table.
    """
    table_rows = browser.find_by_tag('tr', available_tours_table, multiple=True)

    # Ignore the buttons for making a reservation, only interested in the tour details.
    str_to_ignore = 'Reserve'

    # Extract the table content.
    table_header = []
    table_data_rows = []

    for i, table_row in enumerate(table_rows):
        row_content = [
            col.text.strip()
            for col in browser.find_by_tag('td', table_row, multiple=True)
            if str_to_ignore not in col.text
        ]

        if i == 0:
            # The top row lists the headings.
            table_header = row_content
        else:
            table_data_rows.append(row_content)

    return code_block(tabulate(tabular_data=table_data_rows, headers=table_header, tablefmt='psql'), language='text')
