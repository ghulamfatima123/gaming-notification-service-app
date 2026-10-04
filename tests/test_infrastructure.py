"""In-memory adapters: event bus, preference repository, WebSocket channel."""

from __future__ import annotations

import logging

from src.domain.events import BaseEvent, LevelUpEvent, NewFollowerEvent
from src.domain.notification import Notification, NotificationCategory
from src.infrastructure.channels.websocket_channel import WebSocketChannel
from src.infrastructure.memory_event_bus import InMemoryEventBus
from src.infrastructure.memory_prefs_repo import InMemoryPreferenceRepository

# --------------------------------------------------------------------------- #
# Event bus
# --------------------------------------------------------------------------- #


async def test_bus_fans_out_to_every_matching_subscriber():
    bus, received = InMemoryEventBus(), []

    async def first(event):
        received.append(("first", event.event_type))

    async def second(event):
        received.append(("second", event.event_type))

    bus.subscribe(LevelUpEvent, first)
    bus.subscribe(LevelUpEvent, second)
    await bus.publish(LevelUpEvent(player_id=1, new_level=2))

    assert sorted(received) == [("first", "level_up"), ("second", "level_up")]


async def test_bus_routes_by_type_and_base_class_catches_all():
    bus, level_ups, everything = InMemoryEventBus(), [], []

    async def on_level_up(event):
        level_ups.append(event)

    async def on_any(event):
        everything.append(event)

    bus.subscribe(LevelUpEvent, on_level_up)
    bus.subscribe(BaseEvent, on_any)
    await bus.publish(LevelUpEvent(player_id=1, new_level=2))
    await bus.publish(NewFollowerEvent(follower_id=2, followee_id=1))

    assert len(level_ups) == 1
    assert len(everything) == 2


async def test_failing_subscriber_is_isolated_and_logged(caplog):
    bus, received = InMemoryEventBus(), []

    async def broken(event):
        raise RuntimeError("boom")

    async def healthy(event):
        received.append(event)

    bus.subscribe(LevelUpEvent, broken)
    bus.subscribe(LevelUpEvent, healthy)
    with caplog.at_level(logging.ERROR):
        await bus.publish(LevelUpEvent(player_id=1, new_level=2))  # must not raise

    assert len(received) == 1
    assert "failed for LevelUpEvent" in caplog.text


async def test_publish_without_subscribers_is_a_no_op():
    await InMemoryEventBus().publish(LevelUpEvent(player_id=1, new_level=2))


# --------------------------------------------------------------------------- #
# Preference repository
# --------------------------------------------------------------------------- #


async def test_repository_returns_defaults_for_unknown_players():
    prefs = await InMemoryPreferenceRepository().get(42)
    assert prefs.player_id == 42
    assert prefs.is_enabled(NotificationCategory.SOCIAL)


async def test_repository_persists_per_player():
    repo = InMemoryPreferenceRepository()
    await repo.set((await repo.get(1)).with_category(NotificationCategory.SOCIAL, False))

    assert not (await repo.get(1)).is_enabled(NotificationCategory.SOCIAL)
    assert (await repo.get(2)).is_enabled(NotificationCategory.SOCIAL)


# --------------------------------------------------------------------------- #
# WebSocket channel
# --------------------------------------------------------------------------- #


class FakeSocket:
    def __init__(self, broken: bool = False) -> None:
        self.broken = broken
        self.messages: list[dict] = []

    async def send_json(self, data: dict) -> None:
        if self.broken:
            raise RuntimeError("connection closed")
        self.messages.append(data)


def _notification(recipient_id: int = 1) -> Notification:
    return Notification(
        recipient_id=recipient_id,
        category=NotificationCategory.GAME,
        event_type="level_up",
        title="Level Up!",
        message="Congratulations! You've reached level 2!",
    )


async def test_channel_delivers_to_every_socket_of_the_recipient_only():
    channel = WebSocketChannel()
    tab_a, tab_b, other = FakeSocket(), FakeSocket(), FakeSocket()
    channel.register(1, tab_a)
    channel.register(1, tab_b)
    channel.register(2, other)

    await channel.send(_notification(recipient_id=1))

    assert len(tab_a.messages) == len(tab_b.messages) == 1
    assert other.messages == []
    message = tab_a.messages[0]
    assert message["type"] == "notification"
    assert message["data"]["recipient_id"] == 1


async def test_channel_drops_notifications_for_offline_players(caplog):
    channel = WebSocketChannel()
    with caplog.at_level(logging.INFO):
        await channel.send(_notification(recipient_id=9))  # must not raise
    assert "offline" in caplog.text


async def test_channel_removes_dead_sockets_and_keeps_healthy_ones():
    channel = WebSocketChannel()
    dead, alive = FakeSocket(broken=True), FakeSocket()
    channel.register(1, dead)
    channel.register(1, alive)

    await channel.send(_notification())
    await channel.send(_notification())

    assert len(alive.messages) == 2
    assert channel.is_online(1)
    channel.unregister(1, alive)
    assert not channel.is_online(1)
