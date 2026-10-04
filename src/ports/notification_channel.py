"""Port: a delivery channel (in-app WebSocket, push, email, ...)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.notification import Notification


class INotificationChannel(ABC):
    """Adapter boundary between the router and a concrete transport."""

    @abstractmethod
    async def send(self, notification: Notification) -> None:
        """Deliver ``notification`` to ``notification.recipient_id``."""
