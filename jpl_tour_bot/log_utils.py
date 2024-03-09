"""Helper functions for setting up a logger."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from traceback import format_exception
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

LOGGER = logging.getLogger(__name__)


class _CaptureHandler(logging.Handler):
    """Logging handler to store log messages for future processing."""

    def __init__(self, level: int = logging.NOTSET) -> None:
        """Define custom lists in which to store warning and error messages."""
        super().__init__(level)

        self.warnings: list[str] = []
        self.errors: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """
        Store messages from a logged message.

        :param record: The log record captured by this handler.
        """
        log_message = record.getMessage()

        # Extract the message from any Exceptions or Warnings included in this log record.
        if isinstance(record.exc_info, tuple) and isinstance(record.exc_info[1], Exception):
            issue: Warning | Exception = record.exc_info[1]

            # Add the log message as a note to the Exception (PEP 678).
            add_note(issue, log_message)

            # Store the exception message and notes, without the stacktrace.
            log_message = _format_exception_message(issue, include_tb=False)

        if record.levelno == logging.WARNING:
            self.warnings.append(log_message)
        elif record.levelno >= logging.ERROR:
            self.errors.append(log_message)


class StoreWarningsErrors:
    """Context manager for capturing all log messages within the block, storing them for future processing."""

    def __init__(self, logger: str, min_log_level: int) -> None:
        """
        Initialise the context manager.

        :param logger: The name of the logger for which to capture messages.
        :param min_log_level: Capture log messages with at least this severity.
        """
        self._logger = logging.getLogger(logger)
        self._capture_handler = _CaptureHandler(level=min_log_level)

        # Initialise the output variables.
        self.warnings = self._capture_handler.warnings
        self.errors = self._capture_handler.errors

    def __enter__(self) -> StoreWarningsErrors:
        """When entering a new ``with`` context, add a new handler to the requested logger for capturing the logs."""
        self._logger.addHandler(self._capture_handler)
        return self

    def __exit__(
        self, _exc_type: type[BaseException] | None, exc_obj: BaseException | None, _exc_tb: TracebackType | None
    ) -> bool:
        """
        Clean up when leaving a ``with`` context.

        :param _exc_type: The type of any exception that occurred within the context. (Unused)
        :param exc_obj: Any exception that occurred within the context.
        :param _exc_tb: The traceback of any exception that occurred within the context. (Unused)
        """
        self._logger.removeHandler(self._capture_handler)

        if isinstance(exc_obj, Exception):
            self.errors.append(_format_exception_message(exc_obj, include_tb=False))
            LOGGER.error('Top-level failure:', exc_info=exc_obj)

        # The exception has been handled, return `True` to allow code execution to continue.
        return exc_obj is None or isinstance(exc_obj, Exception)


def add_note(issue: Warning | Exception, note: str) -> None:
    """
    Add the string ``note`` to the exception's notes, which appear in the traceback after the exception string.

    Use a custom implementation for compatibility before Python 3.11.
    See: https://docs.python.org/3/library/exceptions.html#BaseException.__notes__

    This implementation mirrors the CPython implementation.
    See: ``BaseException_add_note`` in: https://github.com/python/cpython/blob/main/Objects/exceptions.c
    """
    # Use built-in implementation on Python 3.11 onwards.
    if sys.version_info[:2] >= (3, 11):
        issue.add_note(note)
        return

    # Use the custom implementation on earlier Python versions.
    # The built-in Exception type doesn't have a `__notes__` field;
    # type checking is performed in code, so ignore linter errors here.

    if not isinstance(note, str):
        raise TypeError('note must be a str, not %s', type(note))

    if getattr(issue, '__notes__', None) is None:
        issue.__notes__ = []  # type: ignore[union-attr]

    if not isinstance(issue.__notes__, Sequence):  # type: ignore[union-attr]
        raise TypeError('Cannot add note: __notes__ is not a list')

    issue.__notes__.append(note)  # type: ignore[union-attr, attr-defined]


def _format_exception_message(issue: Warning | Exception, *, include_tb: bool) -> str:
    """
    Format the exception message and notes as a string, optionally including the stacktrace.

    :param issue: The exception object to format.
    :param include_tb: If True, include the exception traceback (keyword only).
    """
    # WebDriverExceptions may have a stacktrace, but it's usually just memory locations in the webdriver,
    # which isn't useful for debugging. Remove this from the stored exception.
    if (st := getattr(issue, 'stacktrace', None)) and isinstance(st, list):
        issue.stacktrace = None  # type: ignore[union-attr]

    # Always include any exception notes in the formatted message.
    # The `traceback.format_exception()` function includes the notes from Python 3.11 onwards,
    # but a custom implementation is required in Python 3.10.
    notes = ''
    if sys.version_info[:2] <= (3, 10) and hasattr(issue, '__notes__') and isinstance(issue.__notes__, Sequence):
        notes = '\n' + '\n'.join(note for note in issue.__notes__)

    return ''.join(format_exception(type(issue), issue, issue.__traceback__ if include_tb else None)).strip() + notes
