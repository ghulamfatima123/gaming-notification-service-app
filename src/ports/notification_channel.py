"""Port: a delivery channel (in-app WebSocket, push, email, ...)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.notification import Notification


class INotificationChannel(ABC):
    """Adapter boundary between the router and a concrete transport."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Deliver ``notification`` to ``notification.recipient_id``.

        Returns ``True`` if it reached the player, ``False`` if they couldn't be
        reached (e.g. offline), so the caller can keep it for later.
        """
