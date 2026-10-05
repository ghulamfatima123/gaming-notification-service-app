"""End-to-end behaviour of the pipeline: producer -> bus -> router -> channel."""

from __future__ import annotations

from typing import Literal

from src.domain.events import BaseEvent, ItemRarity
from src.domain.notification import Notification, NotificationCategory
from src.services.formatters import DEFAULT_FORMATTERS
from src.services.router import NotificationRouter

GAME = NotificationCategory.GAME
SOCIAL = NotificationCategory.SOCIAL


# --------------------------------------------------------------------------- #
# Formatting and delivery
# --------------------------------------------------------------------------- #


async def test_pdf_example_triggers_are_formatted_and_delivered(game, social, channel):
    await game.player_leveled_up(1, 15)
    await game.item_acquired(2, "SwordOfAzeroth", ItemRarity.LEGENDARY)
    await social.friend_request_sent(3, 1)
    await social.friend_request_accepted(1, 3)

    delivered = [(n.recipient_id, n.category, n.message) for n in channel.sent]
    assert delivered == [
        (1, GAME, "Congratulations! You've reached level 15!"),
        (2, GAME, "You've acquired the legendary Sword of Azeroth!"),
        (1, SOCIAL, "Player '3' has sent you a friend request."),
        (3, SOCIAL, "Player '1' accepted your friend request."),
    ]


async def test_pdf_example_triggers_work_exactly_as_written(game, social, channel):
    """The brief's calls, argument for argument (no optional parameters)."""
    await game.player_leveled_up(1, 15)  # gameEngine.playerLeveledUp(1, 15)
    await game.item_acquired(2, "SwordOfAzeroth")  # gameEngine.itemAcquired(2, ...)
    await social.friend_request_sent(3, 1)  # socialSystem.friendRequestSent(3, 1)
    await social.friend_request_accepted(1, 3)  # socialSystem.friendRequestAccepted(1, 3)

    assert [(n.recipient_id, n.event_type) for n in channel.sent] == [
        (1, "level_up"),
        (2, "item_acquired"),
        (1, "friend_request_sent"),
        (3, "friend_request_accepted"),
    ]
    # Without an explicit rarity the item counts as RARE, which is still notified.
    assert channel.sent[1].message == "You've acquired the rare Sword of Azeroth!"


async def test_challenge_and_follower_events_are_delivered(game, social, channel):
    await game.challenge_completed(1, "Dragon Slayer")
    await social.new_follower(follower_id=4, followee_id=1)

    assert [(n.recipient_id, n.category, n.event_type) for n in channel.sent] == [
        (1, GAME, "challenge_completed"),
        (1, SOCIAL, "new_follower"),
    ]
    assert channel.sent[1].actor_id == 4


async def test_pvp_attack_is_routed_only_to_the_defender(game, channel):
    await game.player_attacked(attacker_id=1, defender_id=2)

    assert len(channel.sent) == 1
    notification = channel.sent[0]
    assert notification.recipient_id == 2
    assert notification.actor_id == 1
    assert channel.for_player(1) == []


async def test_pvp_defeat_is_routed_only_to_the_loser(game, channel):
    await game.player_defeated(winner_id=1, loser_id=2)

    assert [(n.recipient_id, n.actor_id, n.message) for n in channel.sent] == [
        (2, 1, "Player '1' has defeated you!")
    ]


async def test_common_items_do_not_notify(game, channel):
    await game.item_acquired(1, "RustyDagger", ItemRarity.COMMON)
    assert channel.sent == []


# --------------------------------------------------------------------------- #
# Preferences
# --------------------------------------------------------------------------- #


async def test_social_opt_out_drops_friend_requests_but_allows_level_ups(
    game, social, channel, opt_out
):
    await opt_out(1, SOCIAL)

    await social.friend_request_sent(3, 1)
    await game.player_leveled_up(1, 16)

    assert [(n.recipient_id, n.event_type) for n in channel.sent] == [(1, "level_up")]


async def test_game_opt_out_drops_game_events_but_allows_social(
    game, social, channel, opt_out
):
    await opt_out(2, GAME)

    await game.player_attacked(attacker_id=1, defender_id=2)
    await social.new_follower(follower_id=1, followee_id=2)

    assert [n.event_type for n in channel.sent] == ["new_follower"]


async def test_opt_out_only_affects_that_player(social, channel, opt_out):
    await opt_out(1, SOCIAL)

    await social.friend_request_sent(3, 1)
    await social.friend_request_sent(3, 2)

    assert [n.recipient_id for n in channel.sent] == [2]


async def test_preferences_are_checked_for_the_recipient_not_the_actor(
    social, channel, opt_out
):
    await opt_out(3, SOCIAL)  # the sender opted out, not the recipient

    await social.friend_request_sent(3, 1)

    assert [n.recipient_id for n in channel.sent] == [1]


async def test_re_enabling_a_category_resumes_delivery(social, channel, prefs, opt_out):
    await opt_out(1, SOCIAL)
    await social.friend_request_sent(3, 1)

    current = await prefs.get(1)
    await prefs.set(current.with_category(SOCIAL, True))
    await social.friend_request_sent(4, 1)

    assert [n.actor_id for n in channel.sent] == [4]


# --------------------------------------------------------------------------- #
# Extensibility
# --------------------------------------------------------------------------- #


class GuildInviteEvent(BaseEvent):
    """An event the production code has never heard of."""

    event_type: Literal["guild_invite"] = "guild_invite"
    inviter_id: int
    invitee_id: int


def format_guild_invite(event: GuildInviteEvent) -> Notification:
    return Notification(
        recipient_id=event.invitee_id,
        actor_id=event.inviter_id,
        category=SOCIAL,
        event_type=event.event_type,
        title="Guild Invite",
        message=f"Player '{event.inviter_id}' invited you to their guild.",
    )


async def test_new_event_type_needs_only_a_new_strategy(bus, prefs, channel):
    router = NotificationRouter(
        prefs, channel, {**DEFAULT_FORMATTERS, GuildInviteEvent: format_guild_invite}
    )
    router.subscribe_to(bus)

    await bus.publish(GuildInviteEvent(inviter_id=1, invitee_id=2))

    assert [(n.recipient_id, n.message) for n in channel.sent] == [
        (2, "Player '1' invited you to their guild.")
    ]


async def test_event_without_a_strategy_is_ignored(prefs, channel):
    router = NotificationRouter(prefs, channel)

    await router.handle(GuildInviteEvent(inviter_id=1, invitee_id=2))

    assert channel.sent == []

