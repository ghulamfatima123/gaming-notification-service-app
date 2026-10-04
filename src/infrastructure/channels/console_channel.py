"""Prints notifications to stdout. Used by the headless demo."""

from __future__ import annotations

from src.domain.notification import Notification
from src.ports.notification_channel import INotificationChannel


class ConsoleChannel(INotificationChannel):
    """A second delivery adapter. The router can't tell it apart from WebSockets."""

    async def send(self, notification: Notification) -> None:
        print(
            f"  -> Player {notification.recipient_id} "
            f"[{notification.category.value.upper()}] {notification.message}"
        )
