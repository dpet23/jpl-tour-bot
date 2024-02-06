"""Scrape the NASA JPL tours and notify if a reservation can be made."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s :: %(levelname)s :: %(name)s:%(lineno)d :: %(message)s',
)

STATE_FILE = Path(__file__).parent / 'jpl_tour.state.json'
URL_JPL_TOUR = 'https://www.jpl.nasa.gov/events/tours/'


@dataclass
class State:
    """State of the JPL tours, saved between script executions."""

    BROWSER_SESSION: str
    NEXT_TOUR_MSG: str | None
    TOUR_AVAILABLE: bool


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


def main() -> None:
    """Find NASA JPL tours and notify of availability."""
    args = Args.parse_args()
    logging.debug(args)

    state = read_state()
    logging.debug(state)


def read_state() -> State:
    """Read and parse the state file. Create a default state if none already exists."""
    if not STATE_FILE.is_file():
        create_state_file()

    with STATE_FILE.open(mode='r', encoding='utf-8') as state_file:
        state_json = json.load(state_file)
    return State(**state_json)


def create_state_file() -> None:
    """Create a new file with a default initial state."""
    new_state = State('', None, False)
    save_state_file(new_state)


def save_state_file(new_state: State) -> None:
    """
    Save the given state to a file.

    :param new_state: The updated state to save.
    """

    class _CustomJSONEncoder(json.JSONEncoder):
        """Custom JSON encoder subclass to serialize dataclasses."""

        def default(self, obj) -> dict[str, Any] | Any:  # noqa: ANN001, ANN401 (missing type, Any type)
            if is_dataclass(obj):
                return asdict(obj)
            return super().default(obj)

    with STATE_FILE.open(mode='w', encoding='utf-8') as state_file:
        json.dump(new_state, state_file, indent=4, cls=_CustomJSONEncoder)
    logging.info('Wrote state to: %s', STATE_FILE.absolute())


if __name__ == '__main__':
    main()
