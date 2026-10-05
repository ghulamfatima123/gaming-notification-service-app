"""Port: holds notifications that couldn't be delivered, until the player returns."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.notification import Notification


class INotificationInbox(ABC):
    """Store-and-forward for offline players."""

    @abstractmethod
    async def add(self, notification: Notification) -> None:
        """Keep ``notification`` for ``notification.recipient_id``."""

    @abstractmethod
    async def drain(self, player_id: int) -> list[Notification]:
        """Return the player's pending notifications (oldest first) and clear them."""
