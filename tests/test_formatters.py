"""Formatting strategies in isolation (pure functions, no async)."""

from __future__ import annotations

import pytest

from src.domain import events
from src.domain.events import (
    BaseEvent,
    FriendRequestAcceptedEvent,
    ItemAcquiredEvent,
    ItemRarity,
    LevelUpEvent,
)
from src.domain.notification import NotificationCategory
from src.services.formatters import (
    DEFAULT_FORMATTERS,
    format_friend_request_accepted,
    format_item_acquired,
    format_level_up,
    humanize_item_name,
)


def _concrete_event_types() -> set[type[BaseEvent]]:
    found, stack = set(), [BaseEvent]
    while stack:
        for sub in stack.pop().__subclasses__():
            stack.append(sub)
            if sub.__module__ == events.__name__ and not sub.__name__.startswith("_"):
                found.add(sub)
    return found


def test_every_domain_event_has_a_strategy():
    assert _concrete_event_types() == set(DEFAULT_FORMATTERS)


def test_level_up_message_matches_spec():
    n = format_level_up(LevelUpEvent(player_id=1, new_level=15))
    assert n.message == "Congratulations! You've reached level 15!"
    assert n.category is NotificationCategory.GAME
    assert n.actor_id is None


def test_friend_accepted_notifies_the_original_requester():
    n = format_friend_request_accepted(FriendRequestAcceptedEvent(accepter_id=1, requester_id=3))
    assert n.recipient_id == 3
    assert n.actor_id == 1


@pytest.mark.parametrize(
    ("rarity", "expected_title"),
    [
        (ItemRarity.RARE, "Rare Item Acquired!"),
        (ItemRarity.EPIC, "Epic Item Acquired!"),
        (ItemRarity.LEGENDARY, "Legendary Item Acquired!"),
    ],
)
def test_valuable_items_notify(rarity, expected_title):
    n = format_item_acquired(ItemAcquiredEvent(player_id=2, item_name="ElvenBow", rarity=rarity))
    assert n is not None
    assert n.title == expected_title
    assert n.message == f"You've acquired the {rarity.value} Elven Bow!"


def test_common_items_produce_no_notification():
    event = ItemAcquiredEvent(player_id=2, item_name="Stick", rarity=ItemRarity.COMMON)
    assert format_item_acquired(event) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SwordOfAzeroth", "Sword of Azeroth"),
        ("sword_of_azeroth", "Sword of Azeroth"),
        ("BladeOfTheAncients", "Blade of the Ancients"),
        ("TheOneRing", "The One Ring"),
        ("Excalibur", "Excalibur"),
        ("AK47Rifle", "AK47 Rifle"),
    ],
)
def test_humanize_item_name(raw, expected):
    assert humanize_item_name(raw) == expected
