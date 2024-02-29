"""Send notifications via Discord posts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from collections.abc import Iterable

    from jpl_tour_bot.bot import Notification

LOGGER = logging.getLogger(__name__)
logging.getLogger('requests').setLevel(logging.WARNING)

# Define the colors that could be used for the left sidebar of each embed.
# https://www.spycolor.com/color-index,g
COLOR_GOOGLE_RED = 0xD50F25
COLOR_GOOGLE_YELLOW = 0xEEB211
COLOR_GOOGLE_GREEN = 0x009925
COLOR_GOOGLE_BLUE = 0x3369E8
COLOR_HTML_GRAY = 0x808080


class _DiscordObject:
    """Parent class for dataclasses, providing common functions."""

    def as_dict(self) -> dict:
        """Convert a dataclass into a dict, keeping only fields with non-None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Embed(_DiscordObject):
    """Discord Embed Object."""

    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: Iterable[dict] = ()


@dataclass
class Field(_DiscordObject):
    """Discord Embed Field Structure."""

    name: str
    value: str
    inline: bool = False


def post_discord(webhook_url: str, messages: list[Notification], warnings: list[str], errors: list[str]) -> None:
    """
    Post a message to a Discord channel.

    .. seealso::
        * https://discord.com/developers/docs/resources/webhook#execute-webhook
        * https://birdie0.github.io/discord-webhooks-guide/discord_webhook.html

    :param webhook_url: Discord webhook URL.
    :param messages: A list of important state changes.
    :param warnings: Any captured warning log messages.
    :param errors: Any captured error log messages or Exception messages.
    """
    LOGGER.debug('Posting to Discord...')

    # Use Discord's "embed" objects for rich text.
    embeds: list[dict] = []

    message_color = COLOR_HTML_GRAY
    message_fields: list[dict] = []
    for notification in messages:
        if 'available tour' in notification.content or notification.title == 'Tour details':
            message_color = COLOR_GOOGLE_GREEN
        elif '(empty)' in notification.content:
            message_color = COLOR_GOOGLE_BLUE
        message_fields.append(Field(name=notification.title, value=notification.content).as_dict())
    if message_fields:
        embeds.append(Embed(color=message_color, fields=message_fields).as_dict())

    warning_fields: list[dict] = []
    for msg in warnings:
        warn_type, warn_msg = msg.split(':', 1)
        warning_fields.append(Field(name=warn_type, value=warn_msg).as_dict())
    if warning_fields:
        embeds.append(Embed(color=COLOR_GOOGLE_YELLOW, fields=warning_fields).as_dict())

    error_fields: list[dict] = []
    for msg in errors:
        exc_type, exc_msg = msg.split(':', 1)
        error_fields.append(Field(name=exc_type, value=exc_msg).as_dict())
    if error_fields:
        embeds.append(Embed(color=COLOR_GOOGLE_RED, fields=error_fields).as_dict())

    # Build the message data.
    payload_json = {'embeds': embeds}

    # Post the message to a channel.
    response = requests.post(url=webhook_url, json=payload_json, timeout=10)

    # Check status code.
    if 200 <= response.status_code <= 299:  # noqa: PLR2004 (magic values)
        LOGGER.info('Message posted to Discord')
    else:
        LOGGER.error(
            'There was a problem posting the message (%d):\n\tWebhook: %s\n\tRequest: %s\n\tResponse: %s',
            response.status_code,
            webhook_url,
            payload_json,
            response.json(),
        )
