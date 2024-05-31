"""Set up package constants."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TOUR_TYPE = 'Visitor Day Tour'  # The type of tour to search for, must be one of the values from the web dropdown.
TOUR_SIZE = 1  # The number of visitors, must be one of the form's allowed values.

_SCRIPT_PATH = Path(__file__).parent
STATE_FILE = _SCRIPT_PATH / 'jpl_tour.state.json'
SCREENSHOT_PATH = _SCRIPT_PATH / 'jpl_tours.png'

URL_JPL_TOUR = 'https://www.jpl.nasa.gov/events/tours/'
BROWSER_DEFAULT_PAGE_TIMEOUT_SEC = 60
BROWSER_WINDOW_SIZE_PX = (1280, 800)


@dataclass
class Args:
    """Define types for each program argument."""

    browser_binary: Path
    ui: bool
    page_timeout: int
    reserve_date_range: list[datetime] | None
    notify: str | None
    wait: list[int] | None

    @staticmethod
    def parse_args() -> Args:
        """
        Parse command line arguments.

        :return: The given arguments, as a typed object.
        """

        def _expanded_file_path(path: str | None) -> Path | None:
            """Expand ``~`` in a given path."""
            if not path:
                return None
            return Path(path).expanduser()

        def _existing_file_path(path: str) -> Path:
            """If the given path doesn't point to a file, raise an exception."""
            expanded_path = _expanded_file_path(path)
            if not expanded_path:
                raise FileNotFoundError('No valid path was given')

            if expanded_path.is_file():
                return expanded_path
            raise FileNotFoundError(path)

        arg_parser = argparse.ArgumentParser(description='Find NASA JPL tours and notify of availability.')
        arg_parser.add_argument(
            '-b',
            '--browser-binary',
            action='store',
            metavar='BIN',
            type=_existing_file_path,
            help='full path to the browser driver binary (REQUIRED)',
        )
        arg_parser.add_argument(
            '-u',
            '--ui',
            action='store_true',
            help='use the browser ui (default: headless)',
        )
        arg_parser.add_argument(
            '-t',
            '--page-timeout',
            action='store',
            metavar='SEC',
            default=BROWSER_DEFAULT_PAGE_TIMEOUT_SEC,
            help=(
                'maximum time to wait for a webpage to load '
                f'(default: {BROWSER_DEFAULT_PAGE_TIMEOUT_SEC/60:.0f} minutes)'
            ),
        )
        arg_parser.add_argument(
            '-r',
            '--reserve-date-range',
            action='store',
            nargs=2,
            metavar=('MIN', 'MAX'),
            type=datetime.fromisoformat,
            help='Press the Reserve button for the 1st tour within the date range (in ISO 8601 format), implies --ui',
        )
        arg_parser.add_argument(
            '-n',
            '--notify',
            action='store',
            metavar='DEST',
            help='set the notification Discord webhook',
        )
        arg_parser.add_argument(
            '-w',
            '--wait',
            action='store',
            nargs=2,
            metavar=('MIN', 'MAX'),
            type=int,
            help='before running the bot, wait some time between MIN and MAX seconds',
        )

        args = Args(**vars(arg_parser.parse_args()))

        # `--reserve-date-range` implies `--ui`
        if args.reserve_date_range:
            args.ui = True

        return args
