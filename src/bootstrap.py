"""Composition root: the one place where concrete adapters are wired to the core."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.memory_event_bus import InMemoryEventBus
from src.infrastructure.memory_prefs_repo import InMemoryPreferenceRepository
from src.ports.event_bus import IEventBus
from src.ports.notification_channel import INotificationChannel
from src.ports.preference_repository import IPreferenceRepository
from src.producers.game_engine import GameEngine
from src.producers.social_system import SocialSystem
from src.services.router import NotificationRouter


@dataclass(frozen=True)
class NotificationSystem:
    bus: IEventBus
    preferences: IPreferenceRepository
    router: NotificationRouter
    game: GameEngine
    social: SocialSystem


def build_system(channel: INotificationChannel) -> NotificationSystem:
    """Wire the in-memory adapters to the router and producers.

    The delivery channel is injected: the server passes a WebSocketChannel and
    the headless demo passes a ConsoleChannel. The pipeline is identical.
    """
    bus = InMemoryEventBus()
    preferences = InMemoryPreferenceRepository()
    router = NotificationRouter(preferences, channel)
    router.subscribe_to(bus)
    return NotificationSystem(
        bus=bus,
        preferences=preferences,
        router=router,
        game=GameEngine(bus),
        social=SocialSystem(bus),
    )
