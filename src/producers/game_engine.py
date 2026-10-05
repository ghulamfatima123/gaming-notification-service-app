"""Simulated game engine: emits gameplay events and knows nothing about notifications."""

from __future__ import annotations

from src.domain.events import (
    ChallengeCompletedEvent,
    ItemAcquiredEvent,
    ItemRarity,
    LevelUpEvent,
    PvPAttackedEvent,
    PvPDefeatedEvent,
)
from src.ports.event_bus import IEventBus


class GameEngine:
    def __init__(self, bus: IEventBus) -> None:
        self._bus = bus

    async def player_leveled_up(self, player_id: int, new_level: int) -> None:
        await self._bus.publish(LevelUpEvent(player_id=player_id, new_level=new_level))

    async def item_acquired(
        self, player_id: int, item_name: str, rarity: ItemRarity = ItemRarity.RARE
    ) -> None:
        await self._bus.publish(
            ItemAcquiredEvent(player_id=player_id, item_name=item_name, rarity=rarity)
        )

    async def challenge_completed(self, player_id: int, challenge_name: str) -> None:
        await self._bus.publish(
            ChallengeCompletedEvent(player_id=player_id, challenge_name=challenge_name)
        )

    async def player_attacked(self, attacker_id: int, defender_id: int) -> None:
        await self._bus.publish(
            PvPAttackedEvent(attacker_id=attacker_id, defender_id=defender_id)
        )

    async def player_defeated(self, winner_id: int, loser_id: int) -> None:
        await self._bus.publish(PvPDefeatedEvent(winner_id=winner_id, loser_id=loser_id))
