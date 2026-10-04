"""Dictionary-backed implementation of IPreferenceRepository."""

from __future__ import annotations

from src.domain.preferences import NotificationPreferences
from src.ports.preference_repository import IPreferenceRepository


class InMemoryPreferenceRepository(IPreferenceRepository):
    """Maps player IDs to their preferences.

    Players with nothing stored get the defaults (all categories enabled).
    The stored values are immutable, so no defensive copies are needed. There
    is no lock either, because everything runs on a single asyncio event loop.
    """

    def __init__(self) -> None:
        self._store: dict[int, NotificationPreferences] = {}

    async def get(self, player_id: int) -> NotificationPreferences:
        return self._store.get(player_id) or NotificationPreferences.default(player_id)

    async def set(self, preferences: NotificationPreferences) -> None:
        self._store[preferences.player_id] = preferences
