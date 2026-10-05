"""Headless walkthrough of the notification pipeline.

Runs the challenge's example triggers through the real event bus, router and
preferences, printing each delivered notification. No server or browser needed:

    python demo.py
"""

from __future__ import annotations

import asyncio

from src.bootstrap import build_system
from src.domain import ItemRarity, NotificationCategory
from src.infrastructure.channels import ConsoleChannel


def step(title: str) -> None:
    print(f"\n=== {title} ===")


async def main() -> None:
    system = build_system(ConsoleChannel())
    game, social = system.game, system.social

    step("1. Example triggers from the challenge brief")
    await game.player_leveled_up(1, 15)  # gameEngine.playerLeveledUp(1, 15)
    await game.item_acquired(2, "SwordOfAzeroth", ItemRarity.LEGENDARY)
    await social.friend_request_sent(3, 1)  # socialSystem.friendRequestSent(3, 1)
    await social.friend_request_accepted(1, 3)  # socialSystem.friendRequestAccepted(1, 3)

    step("2. Other supported events")
    await game.challenge_completed(1, "Dragon Slayer")
    await game.player_attacked(attacker_id=1, defender_id=2)  # only the defender
    await game.player_defeated(winner_id=1, loser_id=2)  # only the loser
    await social.new_follower(4, 1)

    step("3. Common items are not worth a notification")
    await game.item_acquired(1, "RustyDagger", ItemRarity.COMMON)
    print("  (nothing delivered, as expected)")

    step("4. Player 1 turns off SOCIAL notifications")
    prefs = await system.preferences.get(1)
    await system.preferences.set(prefs.with_category(NotificationCategory.SOCIAL, False))
    await social.friend_request_sent(5, 1)
    print("  (friend request from player 5 suppressed)")
    await game.player_leveled_up(1, 16)
    print("  (GAME notifications still arrive)")


if __name__ == "__main__":
    asyncio.run(main())
