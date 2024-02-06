"""Set up package constants."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

STATE_FILE = Path(__file__).parent / 'jpl_tour.state.json'
URL_JPL_TOUR = 'https://www.jpl.nasa.gov/events/tours/'


@dataclass
class Args:
    """Define types for each program argument."""

    browser_binary: Path
    ui: bool
    notify: str
    verbose: bool

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

        required_group = arg_parser.add_mutually_exclusive_group(required=True)
        # required_group.add_argument(
        #     '-d', '--debug-mode',
        #     action='store_true',
        #     help='use debug mode to verify that the essential parts work as expected',
        # )
        required_group.add_argument(
            '-b',
            '--browser-binary',
            action='store',
            metavar='BIN',
            type=_existing_file_path,
            help='full path to the browser driver binary (REQUIRED)',
        )

        arg_parser.add_argument('-u', '--ui', action='store_true', help='use the browser ui, default is headless')
        arg_parser.add_argument(
            '-n',
            '--notify',
            action='store',
            metavar='DEST',
            help='set the notification email address or Discord webhook',
        )
        arg_parser.add_argument(
            '-v', '--verbose', action='store_true', help='verbose logging (debug level and extra console printing)'
        )
        return Args(**vars(arg_parser.parse_args()))
