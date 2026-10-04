"""Domain invariants: validation and immutability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.events import (
    FriendRequestAcceptedEvent,
    FriendRequestSentEvent,
    LevelUpEvent,
    NewFollowerEvent,
    PvPAttackedEvent,
)
from src.domain.notification import Notification, NotificationCategory
from src.domain.preferences import NotificationPreferences

GAME = NotificationCategory.GAME
SOCIAL = NotificationCategory.SOCIAL


@pytest.mark.parametrize(
    ("event_type", "fields"),
    [
        (PvPAttackedEvent, {"attacker_id": 1, "defender_id": 1}),
        (FriendRequestSentEvent, {"sender_id": 1, "recipient_id": 1}),
        (FriendRequestAcceptedEvent, {"accepter_id": 1, "requester_id": 1}),
        (NewFollowerEvent, {"follower_id": 1, "followee_id": 1}),
    ],
)
def test_players_cannot_target_themselves(event_type, fields):
    with pytest.raises(ValidationError, match="must be different players"):
        event_type(**fields)


@pytest.mark.parametrize("level", [0, -3])
def test_level_must_be_positive(level):
    with pytest.raises(ValidationError):
        LevelUpEvent(player_id=1, new_level=level)


def test_events_are_immutable_and_uniquely_identified():
    a = LevelUpEvent(player_id=1, new_level=2)
    b = LevelUpEvent(player_id=1, new_level=2)
    assert a.event_id != b.event_id
    with pytest.raises(ValidationError):
        a.new_level = 3


def test_notification_is_immutable():
    n = Notification(recipient_id=1, category=GAME, event_type="x", title="t", message="m")
    with pytest.raises(ValidationError):
        n.message = "changed"


def test_preferences_default_to_all_enabled():
    prefs = NotificationPreferences.default(1)
    assert prefs.is_enabled(GAME)
    assert prefs.is_enabled(SOCIAL)


def test_missing_category_counts_as_enabled():
    prefs = NotificationPreferences(player_id=1, enabled={})
    assert prefs.is_enabled(SOCIAL)


def test_with_category_returns_a_new_copy():
    original = NotificationPreferences.default(1)
    updated = original.with_category(SOCIAL, False)

    assert original.is_enabled(SOCIAL)
    assert not updated.is_enabled(SOCIAL)
    assert updated.is_enabled(GAME)
