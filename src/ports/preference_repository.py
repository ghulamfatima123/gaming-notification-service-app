"""Port: storage for per-player notification preferences."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.preferences import NotificationPreferences


class IPreferenceRepository(ABC):
    """Async so a database-backed adapter can replace the in-memory one."""

    @abstractmethod
    async def get(self, player_id: int) -> NotificationPreferences:
        """Return the player's preferences, or defaults if none are stored."""

    @abstractmethod
    async def set(self, preferences: NotificationPreferences) -> None:
        """Create or replace the preferences for ``preferences.player_id``."""
