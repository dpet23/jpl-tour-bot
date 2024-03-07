"""Set up a webdriver."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, overload

import psutil
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver as SeleniumChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver as SeleniumRemoteWebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from jpl_tour_bot import BROWSER_DEFAULT_PAGE_TIMEOUT_SEC, BROWSER_WINDOW_SIZE_PX

if TYPE_CHECKING:
    from pathlib import Path

    from selenium.webdriver.remote.webelement import WebElement

LOGGER = logging.getLogger(__name__)


class _CustomWebDriver(SeleniumRemoteWebDriver):
    """Provide helper functions for common browser tasks."""

    # --------------- Webpage Utils ---------------- #

    def open_url(self, url: str) -> None:
        """
        Load a web page in the current session.

        :param url: The URL to load.
        """
        LOGGER.info('Loading "%s"', url)
        try:
            self.get(url)
        except Exception:
            LOGGER.exception('Failed to open URL "%s"', url)

    # ------------- Locating Elements -------------- #

    @overload
    def _find_element(
        self, locator: str, selector: str, parent: WebElement | None = None, *, multiple: Literal[False] = False
    ) -> WebElement: ...

    @overload
    def _find_element(
        self, locator: str, selector: str, parent: WebElement | None = None, *, multiple: Literal[True]
    ) -> list[WebElement]: ...

    @overload
    def _find_element(
        self, locator: str, selector: str, parent: WebElement | None = None, *, multiple: bool
    ) -> WebElement | list[WebElement]: ...

    def _find_element(
        self, locator: str, selector: str, parent: WebElement | None = None, *, multiple: bool = False
    ) -> WebElement | list[WebElement]:
        """
        Find DOM element.

        :param locator: Locator strategy to pick a selector.
        :param selector: String to locate a selector using the strategy.
        :param parent: DOM element in which to search. The browser by default.
        :param multiple: Whether to find multiple elements (keyword only).
        :return: Single element: the first matching DOM element found, or None.
                 Multiple elements: a list of matching elements.
        :raise NoSuchElementException: If no element was found.
        """
        search_element = parent or self
        func = search_element.find_elements if multiple else search_element.find_element
        return func(locator, selector)

    def find_by_class(self, class_name: str, parent: WebElement | None = None) -> WebElement | None:
        """
        Find DOM element by class name.

        :param class_name: Class name of HTML object.
        :param parent: DOM element in which to search. The browser by default.
        :return: The first matching DOM element found, or None.
        """
        LOGGER.debug('Searching for DOM element with class "%s"', class_name)
        try:
            return self._find_element(By.CLASS_NAME, class_name, parent, multiple=False)
        except NoSuchElementException:
            LOGGER.error('Could not find element with class: %s', class_name)  # noqa: TRY400 (don't log stacktrace)
            return None

    @overload
    def find_by_tag(
        self, selector: str, parent: WebElement | None = None, *, multiple: Literal[False] = False
    ) -> WebElement | None: ...

    @overload
    def find_by_tag(
        self, selector: str, parent: WebElement | None = None, *, multiple: Literal[True]
    ) -> list[WebElement]: ...

    def find_by_tag(
        self, selector: str, parent: WebElement | None = None, *, multiple: bool = False
    ) -> WebElement | None | list[WebElement]:
        """
        Find DOM element by HTML tag name.

        :param selector: HTML element to search for.
        :param parent: DOM element in which to search. The browser by default.
        :param multiple: Whether to find multiple elements (keyword only).
        :return: Single element: the first matching DOM element found, or None.
                 Multiple elements: a list of matching elements.
        """
        LOGGER.debug('Searching for HTML element "%s"', selector)
        return self._find_element(By.TAG_NAME, selector, parent, multiple=multiple)

    def find_by_xpath_or_error(self, xpath: str, parent: WebElement | None = None) -> WebElement | None:
        """
        Find DOM element by XPATH.

        :param xpath: XPATH to search for.
        :param parent: DOM element in which to search. The browser by default.
        :return: The first matching DOM element found, or None.
        :raise NoSuchElementException: If no element was found.
        """
        LOGGER.debug('Searching for HTML element "%s"', xpath)
        return self._find_element(By.XPATH, xpath, parent, multiple=False)

    def find_by_xpath(self, xpath: str, parent: WebElement | None = None) -> WebElement | None:
        """
        Find DOM element by XPATH.

        :param xpath: XPATH to search for.
        :param parent: DOM element in which to search. The browser by default.
        :return: The first matching DOM element found, or None.
        """
        try:
            return self.find_by_xpath_or_error(xpath, parent)
        except NoSuchElementException:
            LOGGER.error('Could not find element by XPATH: %s', xpath)  # noqa: TRY400 (don't log stacktrace)
            return None

    # ------------ Waiting For Elements ------------ #

    def wait_until_visible(self, locator: str, selector: str, timeout: int = BROWSER_DEFAULT_PAGE_TIMEOUT_SEC) -> None:
        """
        Wait until a DOM element is visible.

        :param locator: Locator strategy to pick a selector.
        :param selector: String to locate a selector using the strategy.
        :param timeout: Number of seconds before timing out.
        """
        LOGGER.debug('Waiting for element "%s" to be visible', selector)
        WebDriverWait(self, timeout).until(ec.visibility_of_element_located((locator, selector)))

    # ------------------- Other -------------------- #

    def save_screenshot_full_page(self, path: str) -> None:
        """
        Save a screenshot of the full page body to a PNG image file.

        :param filename: The full path to save the screenshot. Should end with a .png extension.
        """
        original_size = self.get_window_size()

        required_width = self.execute_script('return document.body.parentNode.scrollWidth')
        required_height = self.execute_script('return document.body.parentNode.scrollHeight')
        self.set_window_size(required_width, required_height)

        # self.save_screenshot(path)  # has scrollbar
        self._find_element(By.TAG_NAME, 'body').screenshot(path)  # avoids scrollbar
        LOGGER.info('Saved screenshot to: %s', path)

        self.set_window_size(original_size['width'], original_size['height'])

    def shut_down(self) -> None:
        """Close a webdriver."""
        browser_name = self.capabilities['browserName']
        browser_session = self.session_id

        self.quit()
        LOGGER.info('Closed %s (session %s)', browser_name, browser_session)


class ChromeWebDriver(_CustomWebDriver, SeleniumChromeWebDriver):
    """Starts a new Chrome session. Supports custom helper functions."""

    @staticmethod
    def start_new_session(
        executable_path: Path, page_load_timeout: int = BROWSER_DEFAULT_PAGE_TIMEOUT_SEC, *, headless: bool
    ) -> ChromeWebDriver:
        """
        Start a new browser session.

        :param executable_path: Full path to the webdriver binary.
        :param page_load_timeout: Amount of time to wait for a page load to complete.
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

        browser.set_page_load_timeout(page_load_timeout)
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
