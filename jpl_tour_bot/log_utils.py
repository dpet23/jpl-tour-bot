"""Helper functions for setting up a logger."""

from __future__ import annotations

import logging
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
            # Use a custom implementation for compatibility before Python 3.11.
            # See: https://docs.python.org/3/library/exceptions.html#BaseException.__notes__
            if getattr(issue, '__notes__', None) is None:
                issue.__notes__ = []
            issue.__notes__.append(log_message)

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
            LOGGER.error('Top-level failure', exc_info=exc_obj)

        # The exception has been handled, return `True` to allow code execution to continue.
        return exc_obj is None or isinstance(exc_obj, Exception)


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

    # # FUTURE: for py < 3.11
    # if isinstance(self.__notes__, collections.abc.Sequence):
    #     for note in self.__notes__:
    #         note = _safe_string(note, 'note')
    #         yield from [l + '\n' for l in note.split('\n')]

    return ''.join(format_exception(type(issue), issue, issue.__traceback__ if include_tb else None)).strip()
