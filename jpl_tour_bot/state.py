"""The state to save between script executions."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, is_dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass
class State:
    """State of the JPL tours, saved between script executions."""

    BROWSER_SESSION: str
    NEXT_TOUR_MSG: str
    TOUR_AVAILABLE: str

    @staticmethod
    def _default() -> State:
        return State('', '(empty)', '')

    @classmethod
    def from_file(cls, path: Path) -> State:
        """
        Read and parse a state file. Create a default state if none already exists.

        :param path: Path to the state file to read.
        """
        if not path.is_file():
            cls._default().save_to_file(path)

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
            return cls._default()

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
