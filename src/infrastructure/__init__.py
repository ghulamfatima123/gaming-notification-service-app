"""Infrastructure layer: in-memory adapters implementing the ports."""

from src.infrastructure.channels import WebSocketChannel
from src.infrastructure.memory_event_bus import InMemoryEventBus
from src.infrastructure.memory_inbox import InMemoryNotificationInbox
from src.infrastructure.memory_prefs_repo import InMemoryPreferenceRepository

__all__ = [
    "InMemoryEventBus",
    "InMemoryNotificationInbox",
    "InMemoryPreferenceRepository",
    "WebSocketChannel",
]
