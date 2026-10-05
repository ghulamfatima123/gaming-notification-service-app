"""Ports: abstract interfaces the core depends on; adapters implement them."""

from src.ports.event_bus import EventHandler, IEventBus
from src.ports.notification_channel import INotificationChannel
from src.ports.notification_inbox import INotificationInbox
from src.ports.preference_repository import IPreferenceRepository

__all__ = [
    "EventHandler",
    "IEventBus",
    "INotificationChannel",
    "INotificationInbox",
    "IPreferenceRepository",
]
