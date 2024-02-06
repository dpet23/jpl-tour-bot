"""Set up a webdriver."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import psutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver as SeleniumChromeWebDriver
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumRemoteWebDriver

from jpl_tour_bot import BROWSER_DEFAULT_PAGE_TIMEOUT, BROWSER_WINDOW_SIZE_PX

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class _CustomWebDriver(SeleniumRemoteWebDriver):
    """Provide helper functions for common browser tasks."""

    def shut_down(self) -> None:
        """Close a webdriver."""
        browser_name = self.capabilities['browserName']
        browser_session = self.session_id

        self.quit()
        LOGGER.info('Closed %s (session %s)', browser_name, browser_session)


class ChromeWebDriver(_CustomWebDriver, SeleniumChromeWebDriver):
    """Starts a new Chrome session. Supports custom helper functions."""

    @staticmethod
    def start_new_session(executable_path: Path, *, headless: bool) -> ChromeWebDriver:
        """
        Start a new browser session.

        :param executable_path: Full path to the webdriver binary.
        :param headless: Whether to start the browser UI (keyword only).
        :return: A webdriver running Chrome.
        :raise ProcessLookupError: If a process already exists for the executable.
        """
        # Check if a webdriver process is already running.
        if webdriver_procs := [p.pid for p in psutil.process_iter() if 'chromedriver' in p.name().lower()]:
            raise ProcessLookupError(f'Executable "{executable_path}" is running in process: {webdriver_procs}')

        LOGGER.debug('Starting browser...')

        options = webdriver.ChromeOptions()
        options.add_argument('incognito')
        options.add_argument('mute-audio')
        options.add_argument('disable-gpu')
        options.add_argument('disable-browser-side-navigation')
        options.add_argument('disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        if headless:
            options.add_argument('headless=new')  # Chrome 109 and above

        browser = ChromeWebDriver(service=ChromeService(str(executable_path)), options=options)

        browser.set_page_load_timeout(BROWSER_DEFAULT_PAGE_TIMEOUT)
        browser.set_window_size(*BROWSER_WINDOW_SIZE_PX)

        LOGGER.info(
            'Started %s %s (session %s)',
            browser.capabilities['browserName'],
            browser.capabilities['browserVersion'],
            browser.session_id,
        )
        return browser

    def is_alive(self) -> bool:
        """Check whether the given webdriver currently has a browser open."""
        return self.service is not None and self.service.is_connectable()

    def shut_down(self) -> None:
        """Close a webdriver."""
        if not self.is_alive():
            return
        super().shut_down()
