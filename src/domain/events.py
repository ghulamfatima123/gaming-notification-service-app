"""Domain events emitted by game and social subsystems.

Events describe *facts that happened*. They know nothing about notifications,
categories, or who should be told -- that is decided downstream by the
formatting strategies. This keeps producers (GameEngine, SocialSystem)
fully decoupled from the notification pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    model_validator,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    """Common envelope for every domain event."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=_utcnow)


class _TwoPlayerEvent(BaseEvent):
    """An interaction between two distinct players.

    Subclasses name their (actor, target) fields; a player can't target themselves.
    """

    player_fields: ClassVar[tuple[str, str]]

    @model_validator(mode="after")
    def _players_must_differ(self) -> _TwoPlayerEvent:
        actor, target = self.player_fields
        if getattr(self, actor) == getattr(self, target):
            raise ValueError(f"{actor} and {target} must be different players")
        return self


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


class PvPAttackedEvent(_TwoPlayerEvent):
    """``attacker_id`` attacked ``defender_id``."""

    event_type: Literal["pvp_attacked"] = "pvp_attacked"
    player_fields = ("attacker_id", "defender_id")
    attacker_id: int
    defender_id: int


# --------------------------------------------------------------------------- #
# Social events
# --------------------------------------------------------------------------- #


class FriendRequestSentEvent(_TwoPlayerEvent):
    """``socialSystem.friendRequestSent(sender_id, recipient_id)``"""

    event_type: Literal["friend_request_sent"] = "friend_request_sent"
    player_fields = ("sender_id", "recipient_id")
    sender_id: int
    recipient_id: int


class FriendRequestAcceptedEvent(_TwoPlayerEvent):
    """``socialSystem.friendRequestAccepted(accepter_id, requester_id)``

    ``accepter_id`` accepted the request originally sent by ``requester_id``.
    """

    event_type: Literal["friend_request_accepted"] = "friend_request_accepted"
    player_fields = ("accepter_id", "requester_id")
    accepter_id: int
    requester_id: int


class NewFollowerEvent(_TwoPlayerEvent):
    """``follower_id`` started following ``followee_id``."""

    event_type: Literal["new_follower"] = "new_follower"
    player_fields = ("follower_id", "followee_id")
    follower_id: int
    followee_id: int

