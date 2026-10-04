"""The Notification aggregate: what a player actually receives."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class NotificationCategory(str, Enum):
    """Top-level buckets a player can toggle on or off."""

    GAME = "game"
    SOCIAL = "social"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(BaseModel):
    """An immutable, channel-agnostic notification addressed to one player.

    Delivery adapters serialise it with ``model_dump(mode="json")``.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    recipient_id: int
    category: NotificationCategory
    event_type: str
    title: str
    message: str
    created_at: datetime = Field(default_factory=_utcnow)
