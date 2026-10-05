"""Formatting strategies: one function per event type.

Each strategy turns a domain event into a ``Notification``. It decides three things:
  * **who** is notified (e.g. PvP goes to the defender, not the attacker),
  * **which category** the notification belongs to (used for preferences),
  * **what text** the player sees.

A strategy may return ``None`` to mean "this event doesn't warrant a
notification" (e.g. common items).

To support a new event: write one function here and add it to
``DEFAULT_FORMATTERS``. The router and the producers don't change.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

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
    PvPDefeatedEvent,
)
from src.domain.notification import Notification, NotificationCategory

# Each strategy accepts its own concrete event type. The registry below
# guarantees the pairing, so the shared signature is typed loosely.
Formatter = Callable[[Any], Optional[Notification]]

_SMALL_WORDS = {"a", "an", "and", "of", "the", "in", "on", "to", "for"}


def humanize_item_name(raw: str) -> str:
    """``"SwordOfAzeroth"`` / ``"sword_of_azeroth"`` -> ``"Sword of Azeroth"``."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw.replace("_", " ")).split()
    return " ".join(
        word.lower()
        if i > 0 and word.lower() in _SMALL_WORDS
        else word[:1].upper() + word[1:]
        for i, word in enumerate(words)
    )


# --------------------------------------------------------------------------- #
# Game strategies
# --------------------------------------------------------------------------- #


def format_level_up(event: LevelUpEvent) -> Notification:
    return Notification(
        recipient_id=event.player_id,
        category=NotificationCategory.GAME,
        event_type=event.event_type,
        title="Level Up!",
        message=f"Congratulations! You've reached level {event.new_level}!",
    )


def format_item_acquired(event: ItemAcquiredEvent) -> Optional[Notification]:
    # The spec only asks to notify for "rare or valuable" items.
    if event.rarity is ItemRarity.COMMON:
        return None
    rarity = event.rarity.value
    return Notification(
        recipient_id=event.player_id,
        category=NotificationCategory.GAME,
        event_type=event.event_type,
        title=f"{rarity.capitalize()} Item Acquired!",
        message=f"You've acquired the {rarity} {humanize_item_name(event.item_name)}!",
    )


def format_challenge_completed(event: ChallengeCompletedEvent) -> Notification:
    return Notification(
        recipient_id=event.player_id,
        category=NotificationCategory.GAME,
        event_type=event.event_type,
        title="Challenge Completed!",
        message=f"Well done! You've completed '{event.challenge_name}'.",
    )


def format_pvp_attacked(event: PvPAttackedEvent) -> Notification:
    return Notification(
        recipient_id=event.defender_id,
        actor_id=event.attacker_id,
        category=NotificationCategory.GAME,
        event_type=event.event_type,
        title="You're Under Attack!",
        message=f"Player '{event.attacker_id}' has attacked you!",
    )


def format_pvp_defeated(event: PvPDefeatedEvent) -> Notification:
    return Notification(
        recipient_id=event.loser_id,
        actor_id=event.winner_id,
        category=NotificationCategory.GAME,
        event_type=event.event_type,
        title="Defeated!",
        message=f"Player '{event.winner_id}' has defeated you!",
    )


# --------------------------------------------------------------------------- #
# Social strategies
# --------------------------------------------------------------------------- #


def format_friend_request_sent(event: FriendRequestSentEvent) -> Notification:
    return Notification(
        recipient_id=event.recipient_id,
        actor_id=event.sender_id,
        category=NotificationCategory.SOCIAL,
        event_type=event.event_type,
        title="New Friend Request",
        message=f"Player '{event.sender_id}' has sent you a friend request.",
    )


def format_friend_request_accepted(event: FriendRequestAcceptedEvent) -> Notification:
    return Notification(
        recipient_id=event.requester_id,
        actor_id=event.accepter_id,
        category=NotificationCategory.SOCIAL,
        event_type=event.event_type,
        title="Friend Request Accepted",
        message=f"Player '{event.accepter_id}' accepted your friend request.",
    )


def format_new_follower(event: NewFollowerEvent) -> Notification:
    return Notification(
        recipient_id=event.followee_id,
        actor_id=event.follower_id,
        category=NotificationCategory.SOCIAL,
        event_type=event.event_type,
        title="New Follower",
        message=f"Player '{event.follower_id}' started following you.",
    )


# --------------------------------------------------------------------------- #
# Registry: event type -> strategy
# --------------------------------------------------------------------------- #

DEFAULT_FORMATTERS: dict[type[BaseEvent], Formatter] = {
    LevelUpEvent: format_level_up,
    ItemAcquiredEvent: format_item_acquired,
    ChallengeCompletedEvent: format_challenge_completed,
    PvPAttackedEvent: format_pvp_attacked,
    PvPDefeatedEvent: format_pvp_defeated,
    FriendRequestSentEvent: format_friend_request_sent,
    FriendRequestAcceptedEvent: format_friend_request_accepted,
    NewFollowerEvent: format_new_follower,
}
