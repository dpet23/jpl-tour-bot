"""Scrape the NASA JPL tours webpage."""

from __future__ import annotations

import logging
import random
import time
from contextlib import suppress
from datetime import datetime, timedelta
from textwrap import indent
from typing import NamedTuple

from markdown_strings import code_block  # type: ignore[import-untyped]
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from tabulate import tabulate

from jpl_tour_bot import SCREENSHOT_PATH, URL_JPL_TOUR, Args
from jpl_tour_bot.browser import ChromeWebDriver
from jpl_tour_bot.state import State

LOGGER = logging.getLogger(__name__)


ReservationDetails = tuple[list[str], WebElement]


class Notification(NamedTuple):
    """An important state change to report as a notification."""

    title: str
    content: str

    def __str__(self) -> str:
        """Represent the notification as a string."""
        content = indent(self.content, '\t')  # backslash not allowed in expression portion of f-string
        return f"{self.title}\n{content}"


def run_bot(args: Args, state: State) -> list[Notification]:
    """
    Scrape the NASA JPL tours webpage.

    :param args: The command line arguments.
    :param state: State of the JPL tours, from the previous script execution.
    :return: A list of important state changes to include in a notification.
    """
    if args.wait:
        wait_time = random.randrange(start=min(args.wait), stop=max(args.wait) + 1)
        LOGGER.info('Waiting %d seconds (%s)', wait_time, timedelta(seconds=wait_time))
        time.sleep(wait_time)
    else:
        LOGGER.debug('Starting bot immediately')

    browser = ChromeWebDriver.start_new_session(
        executable_path=args.browser_binary, page_load_timeout=args.page_timeout, headless=not args.ui
    )

    # Ensure we're running in a new session.
    browser_session_id: str = browser.session_id or ''
    if browser_session_id == state.BROWSER_SESSION:
        browser.shut_down()
        raise ValueError('The session ID has not changed from the saved state. Aborting.')
    state.BROWSER_SESSION = browser_session_id

    try:
        return _scrape_tour(browser, state, args.reserve_date_range)
    finally:
        browser.shut_down()


def _scrape_tour(browser: ChromeWebDriver, state: State, reserve_date_range: list[datetime]) -> list[Notification]:
    """
    Find whether any NASA JPL tours are available.

    :param browser: The open browser instance.
    :param state: State of the JPL tours. Will be updated with new values.
    :param reserve_date_range: Press the Reserve button for a tour in this date range.
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
    tour_availability_notifications, reservation_details = _get_tour_availability_after_search(
        browser, reserve_date_range
    )

    # Check if the tour availability has changed.
    tour_availability_msg = '\n'.join(notification.content for notification in tour_availability_notifications)
    if tour_availability_msg != state.TOUR_AVAILABLE:
        for notification in tour_availability_notifications:
            notification_messages.append(notification)
            LOGGER.info(notification)

        state.TOUR_AVAILABLE = tour_availability_msg

    if reservation_details:
        press_button(browser, reservation_details)

    # Give the browser a bit of time before closing.
    time.sleep(1)

    return notification_messages


def _get_next_tour_release_date(browser: ChromeWebDriver) -> str:
    """
    Find the posted message for the date of the next tour release.

    :param browser: The open browser instance.
    :return: The message announcing the date of the next tour release, from the JPL website.
    """
    next_tour_msg = State.NEXT_TOUR_MSG

    text_to_search = 'Next Tours Release Date'
    LOGGER.info('Searching for the %s', text_to_search.lower())
    msg_element = browser.find(By.XPATH, f"//h1[text()='{text_to_search}']/following-sibling::div")
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
    search_form_element = browser.find(
        By.XPATH,
        "//h1[text()='Reserve Here']/following-sibling::div",
        raise_exception=True,
        log_msg='Could not find tour search form',
    )

    LOGGER.info('Selecting the tour type: "%s"', tour_type)
    tour_type_select = browser.find(
        By.XPATH,
        "//select[@name='categoryId']",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find tour type select box',
    )
    Select(tour_type_select).select_by_visible_text(tour_type)

    time.sleep(1)

    LOGGER.info('Entering the number of visitors: %d', tour_size)
    tour_size_input = browser.find(
        By.XPATH,
        "//input[@name='groupSize']",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find tour size input box',
    )
    tour_size_input.send_keys(str(tour_size))

    time.sleep(1)

    LOGGER.info('Submitting the tour search form')
    submit_form_button = browser.find(
        By.XPATH,
        "//button[contains(@class, 'btn-submit')]",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find submit button for the tour search form',
    )
    if not submit_form_button.is_enabled():
        raise RuntimeError('Submit button for the tour search form is not enabled')
    try:
        submit_form_button.click()
    except Exception:
        raise RuntimeError("Can't click on %s", submit_form_button.get_attribute('outerHTML')) from None


def _get_tour_availability_after_search(
    browser: ChromeWebDriver, reserve_date_range: list[datetime]
) -> tuple[list[Notification], ReservationDetails | None]:
    """
    After searching for tours by submitting a form, check if there's any tours available.

    :param browser: The open browser instance.
    :param reserve_date_range: Press the Reserve button for a tour in this date range.
    :return: The availability of the next tours (as a list of notifications to report),
             and the details of the tour to reserve.
    """
    LOGGER.info('Waiting for the tour search to load')
    browser.wait_until_visible(By.XPATH, "//*[@id='primary_column']/div/table")
    time.sleep(5)

    LOGGER.info('Trying to find the error message')
    error_msg_element = browser.find(
        By.XPATH,
        "//*[@id='primary_column']/div/div/label[contains(@class, 'err')]",
        log_msg=None,  # suppress logging if error element was not found
    )

    notification_title_new_availability = 'Tour availability has changed'

    if error_msg_element:
        # No tours are available, return early and include the website's message in a notification.
        return [Notification(notification_title_new_availability, error_msg_element.text.strip())], None

    notifications: list[Notification] = []

    LOGGER.info('Trying to find the number of available tours')
    tour_availability_msg = browser.find(By.CLASS_NAME, 'tour_count')
    if tour_availability_msg:
        tour_availability_notif = Notification(notification_title_new_availability, tour_availability_msg.text.strip())
    else:
        tour_availability_notif = Notification(notification_title_new_availability, 'No tours found.')
    notifications.append(tour_availability_notif)

    LOGGER.info('Parsing the table of available tours')
    available_tours_table = browser.find(By.CLASS_NAME, 'available_tours')
    reservation_details = None
    if available_tours_table:
        try:
            available_tour_details, reservation_details = _parse_available_tours_table(
                browser, available_tours_table, reserve_date_range
            )
        except Exception:
            LOGGER.exception('Could not parse the table of available tours')
            available_tour_details = code_block(available_tours_table.get_attribute('outerHTML') or '', language='html')
        notifications.append(Notification('Tour details', available_tour_details))

    browser.save_screenshot_full_page(str(SCREENSHOT_PATH.absolute()))
    return notifications, reservation_details


def _parse_available_tours_table(
    browser: ChromeWebDriver, available_tours_table: WebElement, reserve_date_range: list[datetime]
) -> tuple[str, ReservationDetails | None]:
    """
    Parse the HTML table of available tours, extracting the details.

    :param browser: The open browser instance.
    :param available_tours_table: Web element representing the table of available tours.
    :param reserve_date_range: Press the Reserve button for a tour in this date range.
    :return: The details of available tours (as a multiline string representing a table),
             and the details of the tour to reserve.
    """
    table_rows = browser.find(By.TAG_NAME, 'tr', available_tours_table, multiple=True, raise_exception=True)

    # Ignore the buttons for making a reservation, only interested in the tour details.
    str_to_ignore = 'Reserve'

    # Extract the table content.
    table_header = []
    table_data_rows = []

    col_index_date = 0
    reservation_details: ReservationDetails | None = None
    row_content = []

    for i, table_row in enumerate(table_rows):
        row_content = [
            col.text.strip()
            for col in browser.find(By.TAG_NAME, 'td', table_row, multiple=True, raise_exception=True)
            if str_to_ignore not in col.text
        ]

        if i == 0:
            # The top row lists the headings.
            table_header = row_content
            with suppress(ValueError):
                col_index_date = table_header.index('Date')
        else:
            table_data_rows.append(row_content)

            if reserve_date_range and not reservation_details:
                tour_date = datetime.strptime(row_content[col_index_date], '%m/%d/%Y')
                if min(reserve_date_range) <= tour_date <= max(reserve_date_range):  # noqa: SIM102 (nested if)
                    if reserve_button := browser.find(By.TAG_NAME, 'button', table_row):
                        reservation_details = (row_content, reserve_button)

    if reservation_details:
        LOGGER.info(
            'List of all available tours:\n%s',
            tabulate(tabular_data=table_data_rows, headers=table_header, tablefmt='psql'),
        )

    return (
        code_block(tabulate(tabular_data=table_data_rows, headers=table_header, tablefmt='psql'), language='text'),
        reservation_details,
    )


def press_button(browser: ChromeWebDriver, reservation_details: ReservationDetails) -> None:
    """
    Press the Reserve button for a tour.

    :param browser: The open browser instance.
    :param reservation_details: The tour details and the button to press.
    """
    tour_details, reserve_button = reservation_details
    LOGGER.warning('Pressing "%s" button for tour: %s', reserve_button.text, ', '.join(tour_details))

    reserve_button.click()
    browser.wait_until_visible(By.XPATH, "//div[contains(@class, 'clock') and normalize-space(text())]")

    time_to_wait = datetime.strptime(browser.find(By.CLASS_NAME, 'clock', raise_exception=True).text, '%M:%S')
    timedelta_to_wait = timedelta(minutes=time_to_wait.minute + 5, seconds=time_to_wait.second)
    LOGGER.info('\n\tWaiting %s to complete the booking form.\n\tUse Ctrl+C to continue.', timedelta_to_wait)
    try:
        time.sleep(timedelta_to_wait.total_seconds())
    except KeyboardInterrupt:
        LOGGER.info('Continuing early.')
    else:
        LOGGER.info('Finished waiting.')
