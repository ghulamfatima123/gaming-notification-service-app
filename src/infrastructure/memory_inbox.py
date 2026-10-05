"""Bounded, in-memory implementation of INotificationInbox."""

from __future__ import annotations

from collections import defaultdict, deque

from src.domain.notification import Notification
from src.ports.notification_inbox import INotificationInbox

DEFAULT_MAX_PER_PLAYER = 50


class InMemoryNotificationInbox(INotificationInbox):
    """Keeps the most recent ``max_per_player`` undelivered notifications per player.

    The cap bounds memory: when it's exceeded, the oldest notification is
    discarded. A durable store (database table, Redis list) would replace this
    adapter so pending notifications survive a restart.
    """

    def __init__(self, max_per_player: int = DEFAULT_MAX_PER_PLAYER) -> None:
        self._pending: dict[int, deque[Notification]] = defaultdict(
            lambda: deque(maxlen=max_per_player)
        )

    async def add(self, notification: Notification) -> None:
        self._pending[notification.recipient_id].append(notification)

    async def drain(self, player_id: int) -> list[Notification]:
        pending = self._pending.pop(player_id, None)
        return list(pending) if pending else []

    async def pending_counts(self) -> dict[int, int]:
        return {player_id: len(queue) for player_id, queue in self._pending.items() if queue}
