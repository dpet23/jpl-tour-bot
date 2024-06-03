"""Scrape the NASA JPL tours webpage."""

from __future__ import annotations

import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple

from markdown_strings import code_block  # type: ignore[import-untyped]
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from tabulate import tabulate

from jpl_tour_bot import SCREENSHOT_PATH, STATE_FILE, TOUR_SIZE, TOUR_TYPE, URL_JPL_TOUR, Args
from jpl_tour_bot.browser import ChromeWebDriver
from jpl_tour_bot.state import State

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

    from jpl_tour_bot.notification import Notification

LOGGER = logging.getLogger(__name__)


class Tour(NamedTuple):
    """The details of an available tour."""

    DATE: str
    TIMES: str
    RESERVE_BUTTON: WebElement | None


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
        notification_messages, tour_details = _scrape_tour(browser, state)

        if args.reserve_date_range and tour_details and state.PRESS_RESERVE_BUTTON:
            continue_pressing_reserve_button = _open_tour_reservation(browser, tour_details, args.reserve_date_range)
            _ = state.set_field(
                'PRESS_RESERVE_BUTTON', continue_pressing_reserve_button, 'Continue pressing reserve button'
            )

        return notification_messages
    finally:
        browser.shut_down()


def _scrape_tour(browser: ChromeWebDriver, state: State) -> tuple[list[Notification], list[Tour]]:
    """
    Find whether any NASA JPL tours are available.

    :param browser: The open browser instance.
    :param state: State of the JPL tours. Will be updated with new values.
    :return: Important state changes to include in a notification,
             and the details of available tours.
    """
    # Open the webpage.
    browser.open_url(URL_JPL_TOUR)

    time.sleep(1)

    notification_messages: list[Notification] = []

    # Search for the date of the next tour release, and check if it has changed.
    next_tour_msg = _get_next_tour_release_date(browser)
    if notification := state.set_field('NEXT_TOUR_MSG', next_tour_msg, 'Next tour message has changed'):
        notification_messages.append(notification)

    time.sleep(1)

    # Search for available tours.
    _submit_tour_search_form(browser)

    # Get details of available tours, and check if the availability has changed.
    tour_availability_msg = _get_tour_availability_after_search(browser)
    if notification := state.set_field('TOUR_AVAILABLE', tour_availability_msg, 'Tour availability has changed'):
        notification_messages.append(notification)

    # Parse the table of available tours.
    tour_details: list[Tour] = []
    if available_tours_table := browser.find(By.CLASS_NAME, 'available_tours', log_msg=None):
        browser.save_screenshot_full_page(str(SCREENSHOT_PATH.absolute()))

        try:
            tour_details, table_header = _parse_available_tours_table(browser, available_tours_table)
        except Exception:
            LOGGER.exception('Could not parse the table of available tours')
            tour_table = code_block(available_tours_table.get_attribute('outerHTML') or '', language='html')
        else:
            tour_table = code_block(_format_available_tours_table(tour_details, table_header), language='text')
        finally:
            if notification := state.set_field('TOUR_TABLE', tour_table, 'Tour details'):
                notification_messages.append(notification)

    return notification_messages, tour_details


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


def _submit_tour_search_form(browser: ChromeWebDriver) -> None:
    """
    Fill out and submit the web form, searching for available tours.

    :param browser: The open browser instance.
    """
    LOGGER.info('Finding the tour search form')
    search_form_element = browser.find(
        By.XPATH,
        "//h1[text()='Reserve Here']/following-sibling::div",
        raise_exception=True,
        log_msg='Could not find tour search form',
    )

    LOGGER.info('Selecting the tour type: "%s"', TOUR_TYPE)
    tour_type_select = browser.find(
        By.XPATH,
        ".//select[@name='categoryId']",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find tour type select box',
    )
    Select(tour_type_select).select_by_visible_text(TOUR_TYPE)

    time.sleep(1)

    LOGGER.info('Entering the number of visitors: %d', TOUR_SIZE)
    tour_size_input = browser.find(
        By.XPATH,
        ".//input[@name='groupSize']",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find tour size input box',
    )
    tour_size_input.send_keys(str(TOUR_SIZE))

    time.sleep(1)

    LOGGER.info('Submitting the tour search form')
    submit_form_button = browser.find(
        By.XPATH,
        ".//button[contains(@class, 'btn-submit')]",
        parent=search_form_element,
        raise_exception=True,
        log_msg='Could not find submit button for the tour search form',
    )
    if not submit_form_button.is_enabled():
        raise RuntimeError('Submit button for the tour search form is not enabled')
    try:
        submit_form_button.click()
    except Exception as e:
        raise RuntimeError("Can't click on %s", submit_form_button.get_attribute('outerHTML')) from e

    # Wait until the gear icon appears (indicating the form is being submitted).
    cog_icon_class = 'fa-cog'
    browser.wait_until_visibility(
        By.CLASS_NAME,
        cog_icon_class,
        visible=True,
        timeout=min(5, browser.timeouts._page_load / 1000),  # type: ignore[attr-defined]
    )

    # Wait until the gear icon disappears (the form has been submitted).
    # At busy times, when new tours are being released, the icon may not disappear. Time out after a while to retry.
    browser.wait_until_visibility(By.CLASS_NAME, cog_icon_class, visible=False)


def _get_tour_availability_after_search(browser: ChromeWebDriver) -> str:
    """
    After searching for tours by submitting a form, check if there's any tours available.

    :param browser: The open browser instance.
    :return: The availability of the next tours, from the JPL website.
    """
    LOGGER.info('Waiting for the tour search to load')
    browser.wait_until_visibility(By.CLASS_NAME, 'tour_type_table', visible=True)
    time.sleep(5)

    LOGGER.info('Trying to find the error message')
    error_msg_element = browser.find(
        By.XPATH,
        "//*[@id='primary_column']/div/div/label[contains(@class, 'err')]",
        log_msg=None,  # suppress logging if error element was not found
    )

    if error_msg_element:
        # No tours are available, return early and include the website's message in a notification.
        return error_msg_element.text.strip()

    LOGGER.info('Trying to find the number of available tours')
    tour_availability_msg = browser.find(By.CLASS_NAME, 'tour_count')
    if tour_availability_msg:
        return tour_availability_msg.text.strip()
    else:
        return 'Not found.'


def _parse_available_tours_table(
    browser: ChromeWebDriver, available_tours_table: WebElement
) -> tuple[list[Tour], list[str]]:
    """
    Extract the details from the HTML table of available tours.

    :param browser: The open browser instance.
    :param available_tours_table: Web element representing the table of available tours.
    :return: The details of available tours (as a list of objects),
             and the contents of the table's header row.
    :raise NoSuchElementException: If various components of the table could not be found.
    """
    tour_details: list[Tour] = []

    # Read the table header row, and extract the text.
    header_cols = browser.find(
        By.XPATH,
        ".//td[contains(@class, 'table_header')]",
        parent=available_tours_table,
        multiple=True,
        raise_exception=True,
    )
    table_header = [col.text.strip() for col in header_cols]

    # Find the indices of the interesting columns,
    index_date = next((i for i, v in enumerate(table_header) if 'Date' in v), 0)
    index_times = next((i for i, v in enumerate(table_header) if 'Time' in v), 1)
    index_button = next((i for i, v in enumerate(table_header) if 'Reserve' in v), 2)

    # Ensure the header text is in the expected order.
    table_header = [table_header[index_date], table_header[index_times], table_header[index_button]]

    # Read the table content rows.
    all_content_cols = browser.find(
        By.XPATH,
        ".//td[contains(@class, 'table_content')]",
        parent=available_tours_table,
        multiple=True,
        raise_exception=True,
    )

    # All row cells were extracted to a single list, need to figure out how long each row actually is.
    if len(all_content_cols) % len(header_cols):
        raise RuntimeError(
            f'The number of content columns ({len(all_content_cols)})'
            f' is not divisible by the number of header columns ({len(header_cols)})'
        )
    num_rows = int(len(all_content_cols) / len(header_cols))

    # Extract the tour date and times, and find the Reservation button for each row.
    for r in range(num_rows):
        index_row = r * len(header_cols)
        tour = Tour(
            all_content_cols[index_row + index_date].text.strip(),
            all_content_cols[index_row + index_times].text.strip(),
            browser.find(
                By.TAG_NAME,
                'button',
                all_content_cols[index_row + index_button],
                log_msg=f'Could not find Reservation button for row #{r+1}',
            ),
        )
        tour_details.append(tour)

    return tour_details, table_header


def _format_available_tours_table(tour_details: list[Tour], table_header: list[str]) -> str:
    """
    Format the details of available tours for pretty-printing.

    :param tour_details: The details of available tours.
    :param table_header: The contents of the table's header row.
    :return: A multiline string representing a table, containing tour details.
    """
    return tabulate(
        tabular_data=[(t.DATE, t.TIMES) for t in tour_details],  # only include the tour date and times
        headers=table_header[:-1],  # assume the table header has been ordered correctly
        tablefmt='psql',
    )


def _open_tour_reservation(
    browser: ChromeWebDriver, tour_details: list[Tour], reserve_date_range: list[datetime]
) -> bool:
    """
    Press the Reserve button for a tour.

    :param browser: The open browser instance.
    :param tour_details: The details of available tours.
    :param reserve_date_range: Only consider tours in this date range (inclusive).
    """
    continue_pressing_reserve_button = True

    # Find all tours that match the date criteria.
    tours_in_range = [
        tour
        for tour in tour_details
        if min(reserve_date_range) <= datetime.strptime(tour.DATE, '%m/%d/%Y') <= max(reserve_date_range)
    ]

    if not tours_in_range:
        return continue_pressing_reserve_button

    # Click the Reservation button for the 1st tour that matches the date criteria.
    selected_tour = tours_in_range[0]
    selected_tour_details = f'{selected_tour.DATE}, {selected_tour.TIMES}'
    if not selected_tour.RESERVE_BUTTON:
        raise NoSuchElementException(f'Could not retrieve button for tour: {selected_tour_details}\n')
    LOGGER.warning(
        'Pressing "%s" button for tour: %s',
        selected_tour.RESERVE_BUTTON.text,
        selected_tour_details,
    )
    selected_tour.RESERVE_BUTTON.click()

    # Wait until the reservation page loads and the timer starts counting down.
    browser.wait_until_visibility(
        By.XPATH, "//div[contains(@class, 'clock') and normalize-space(text())]", visible=True
    )

    # Wait for manual completion of the booking form.
    time_to_wait = datetime.strptime(browser.find(By.CLASS_NAME, 'clock', raise_exception=True).text, '%M:%S')
    timedelta_to_wait = timedelta(minutes=time_to_wait.minute + 5, seconds=time_to_wait.second)
    cancel_signal = signal.SIGINT
    LOGGER.info(
        '\n\tWaiting %s to complete the booking form.\n\tUse Ctrl+C (%s or signal %d) to continue.\n\tProcess ID: %d',
        timedelta_to_wait,
        cancel_signal.name,
        cancel_signal.value,
        os.getpid(),
    )
    try:
        time.sleep(timedelta_to_wait.total_seconds())
    except KeyboardInterrupt:
        LOGGER.info('Continuing early.')
    else:
        LOGGER.info('Finished waiting.')

    if sys.stdin.isatty():
        try:
            made_booking = input('\nWAS THE BOOKING SUCCESSFUL? (y/n): ')
        except KeyboardInterrupt:
            pass  # use default value
        else:
            continue_pressing_reserve_button = not any(
                s == made_booking.lower().strip() for s in ('y', 'yes', 't', 'true')
            )
    else:
        LOGGER.warning(
            (
                'Cannot read input from `stdin`. '
                'If the booking was successful, please update `PRESS_RESERVE_BUTTON` in: %s'
            ),
            STATE_FILE.absolute(),
        )
    return continue_pressing_reserve_button
