"""Domain layer: pure models with no I/O or framework dependencies."""

from src.domain.events import (
    BaseEvent,
    ChallengeCompletedEvent,
    FriendRequestAcceptedEvent,
    FriendRequestSentEvent,
    ItemAcquiredEvent,
    ItemRarity,
    LevelUpEvent,
    NewFollowerEvent,
    PvPAttackedEvent,
)
from src.domain.notification import Notification, NotificationCategory
from src.domain.preferences import NotificationPreferences

__all__ = [
    "BaseEvent",
    "ChallengeCompletedEvent",
    "FriendRequestAcceptedEvent",
    "FriendRequestSentEvent",
    "ItemAcquiredEvent",
    "ItemRarity",
    "LevelUpEvent",
    "NewFollowerEvent",
    "Notification",
    "NotificationCategory",
    "NotificationPreferences",
    "PvPAttackedEvent",
]
