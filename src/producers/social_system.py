"""Simulated social system: emits social events and knows nothing about notifications."""

from __future__ import annotations

from src.domain.events import (
    FriendRequestAcceptedEvent,
    FriendRequestSentEvent,
    NewFollowerEvent,
)
from src.ports.event_bus import IEventBus


class SocialSystem:
    def __init__(self, bus: IEventBus) -> None:
        self._bus = bus

    async def friend_request_sent(self, sender_id: int, recipient_id: int) -> None:
        await self._bus.publish(
            FriendRequestSentEvent(sender_id=sender_id, recipient_id=recipient_id)
        )

    async def friend_request_accepted(self, accepter_id: int, requester_id: int) -> None:
        await self._bus.publish(
            FriendRequestAcceptedEvent(accepter_id=accepter_id, requester_id=requester_id)
        )

    async def new_follower(self, follower_id: int, followee_id: int) -> None:
        await self._bus.publish(
            NewFollowerEvent(follower_id=follower_id, followee_id=followee_id)
        )
