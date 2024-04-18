"""Notifications of important state changes."""

from textwrap import indent
from typing import NamedTuple


class Notification(NamedTuple):
    """An important state change to report as a notification."""

    title: str
    content: str

    def __str__(self) -> str:
        """Represent the notification as a string."""
        content = indent(self.content, '\t')  # backslash not allowed in expression portion of f-string
        return f"{self.title}\n{content}"
