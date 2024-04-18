"""The state to save between script executions."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, is_dataclass
from typing import TYPE_CHECKING, Any

from jpl_tour_bot.notification import Notification

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass
class State:
    """State of the JPL tours, saved between script executions."""

    BROWSER_SESSION: str = ''
    NEXT_TOUR_MSG: str = '(empty)'
    TOUR_AVAILABLE: str = ''
    TOUR_TABLE: str = ''

    @classmethod
    def from_file(cls, path: Path) -> State:
        """
        Read and parse a state file.

        :param path: Path to the state file to read.
        :return: The state parsed from the file, or a default state on error.
        """
        if not path.is_file():
            return State()

        with path.open(mode='r', encoding='utf-8') as state_file:
            state_json = json.load(state_file)

        try:
            return State(**state_json)
        except Exception as ex:
            LOGGER.warning(
                'Failed to parse the existing state file into an object: %s\n%s',
                str(ex),
                json.dumps(state_json, indent=2),
            )
            return State()

    def set_field(self, field: str, msg: str, notification_title: str) -> Notification | None:
        """
        Set the contents of a field, generate a Notification, and log a message.

        :param field: Name of the state field to set.
        :param msg: The value to set for the field.
        :param notification_title: Title for the generated notification.
        :return: A Notification to report te change, or None if no changes were made to the field.
        :raise AttributeError: If the state does not contain a field with the given name.
        """
        if msg == getattr(self, field):
            return None

        setattr(self, field, msg)

        notification = Notification(notification_title, msg)
        LOGGER.info(notification)
        return notification

    def save_to_file(self, path: Path) -> None:
        """
        Save the state to a file.

        :param path: Path to the state file to write.
        """

        class _CustomJSONEncoder(json.JSONEncoder):
            """Custom JSON encoder subclass to serialize dataclasses."""

            def default(self, obj: State) -> dict[str, Any] | Any:  # noqa: ANN401 (Any type)
                if is_dataclass(obj):
                    return asdict(obj)
                return super().default(obj)

        with path.open(mode='w', encoding='utf-8') as state_file:
            json.dump(self, state_file, indent=4, cls=_CustomJSONEncoder)
        LOGGER.info('Wrote to: %s', path.absolute())
