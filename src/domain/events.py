"""Domain events emitted by game and social subsystems.

Events describe *facts that happened*. They know nothing about notifications,
categories, or who should be told -- that is decided downstream by the
formatting strategies. This keeps producers (GameEngine, SocialSystem)
fully decoupled from the notification pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, TypeAdapter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    """Common envelope for every domain event."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=_utcnow)


class ItemRarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


# --------------------------------------------------------------------------- #
# Game events
# --------------------------------------------------------------------------- #


class LevelUpEvent(BaseEvent):
    """``gameEngine.playerLeveledUp(player_id, new_level)``"""

    event_type: Literal["level_up"] = "level_up"
    player_id: int
    new_level: PositiveInt


class ItemAcquiredEvent(BaseEvent):
    """``gameEngine.itemAcquired(player_id, item_name)``"""

    event_type: Literal["item_acquired"] = "item_acquired"
    player_id: int
    item_name: str = Field(min_length=1)
    rarity: ItemRarity = ItemRarity.RARE


class ChallengeCompletedEvent(BaseEvent):
    """A player finished a quest or achievement."""

    event_type: Literal["challenge_completed"] = "challenge_completed"
    player_id: int
    challenge_name: str = Field(min_length=1)


class PvPAttackedEvent(BaseEvent):
    """``attacker_id`` attacked ``defender_id``."""

    event_type: Literal["pvp_attacked"] = "pvp_attacked"
    attacker_id: int
    defender_id: int


# --------------------------------------------------------------------------- #
# Social events
# --------------------------------------------------------------------------- #


class FriendRequestSentEvent(BaseEvent):
    """``socialSystem.friendRequestSent(sender_id, recipient_id)``"""

    event_type: Literal["friend_request_sent"] = "friend_request_sent"
    sender_id: int
    recipient_id: int


class FriendRequestAcceptedEvent(BaseEvent):
    """``socialSystem.friendRequestAccepted(accepter_id, requester_id)``

    ``accepter_id`` accepted the request originally sent by ``requester_id``.
    """

    event_type: Literal["friend_request_accepted"] = "friend_request_accepted"
    accepter_id: int
    requester_id: int


class NewFollowerEvent(BaseEvent):
    """``follower_id`` started following ``followee_id``."""

    event_type: Literal["new_follower"] = "new_follower"
    follower_id: int
    followee_id: int


# --------------------------------------------------------------------------- #
# Parsing raw payloads (e.g. JSON from a WebSocket) into typed events
# --------------------------------------------------------------------------- #

DomainEvent = Annotated[
    Union[
        LevelUpEvent,
        ItemAcquiredEvent,
        ChallengeCompletedEvent,
        PvPAttackedEvent,
        FriendRequestSentEvent,
        FriendRequestAcceptedEvent,
        NewFollowerEvent,
    ],
    Field(discriminator="event_type"),
]

_event_adapter: TypeAdapter[DomainEvent] = TypeAdapter(DomainEvent)


def parse_event(data: dict[str, Any]) -> BaseEvent:
    """Validate a raw dict into the concrete event selected by ``event_type``.

    Raises ``pydantic.ValidationError`` on unknown types or bad fields.
    """
    return _event_adapter.validate_python(data)
