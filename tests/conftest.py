"""Shared fixtures: real in-memory adapters plus a channel that records deliveries."""

from __future__ import annotations

import pytest

from src.domain.notification import Notification, NotificationCategory
from src.infrastructure.memory_event_bus import InMemoryEventBus
from src.infrastructure.memory_inbox import InMemoryNotificationInbox
from src.infrastructure.memory_prefs_repo import InMemoryPreferenceRepository
from src.ports.notification_channel import INotificationChannel
from src.producers.game_engine import GameEngine
from src.producers.social_system import SocialSystem
from src.services.router import NotificationRouter


class RecordingChannel(INotificationChannel):
    """Test double: records deliveries. Players in ``offline`` can't be reached."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []
        self.offline: set[int] = set()

    async def send(self, notification: Notification) -> bool:
        if notification.recipient_id in self.offline:
            return False
        self.sent.append(notification)
        return True

    def for_player(self, player_id: int) -> list[Notification]:
        return [n for n in self.sent if n.recipient_id == player_id]


@pytest.fixture
def bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def prefs() -> InMemoryPreferenceRepository:
    return InMemoryPreferenceRepository()


@pytest.fixture
def channel() -> RecordingChannel:
    return RecordingChannel()


@pytest.fixture
def inbox() -> InMemoryNotificationInbox:
    return InMemoryNotificationInbox()


@pytest.fixture
def router(
    bus: InMemoryEventBus,
    prefs: InMemoryPreferenceRepository,
    channel: RecordingChannel,
    inbox: InMemoryNotificationInbox,
) -> NotificationRouter:
    router = NotificationRouter(prefs, channel, inbox)
    router.subscribe_to(bus)
    return router


@pytest.fixture
def game(bus: InMemoryEventBus, router: NotificationRouter) -> GameEngine:
    return GameEngine(bus)


@pytest.fixture
def social(bus: InMemoryEventBus, router: NotificationRouter) -> SocialSystem:
    return SocialSystem(bus)


@pytest.fixture
def opt_out(prefs: InMemoryPreferenceRepository):
    """``await opt_out(player_id, category)`` disables one category for a player."""

    async def _opt_out(player_id: int, category: NotificationCategory) -> None:
        current = await prefs.get(player_id)
        await prefs.set(current.with_category(category, False))

    return _opt_out
