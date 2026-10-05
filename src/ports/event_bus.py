"""Port: publish/subscribe transport for domain events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from src.domain.events import BaseEvent

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class IEventBus(ABC):
    """Producers publish events; consumers subscribe by event type.

    Producers never learn who (if anyone) is listening.
    """

    @abstractmethod
    def subscribe(self, event_type: type[BaseEvent], handler: EventHandler) -> None:
        """Register ``handler`` for ``event_type`` (and its subclasses)."""

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Deliver ``event`` to every matching subscriber."""
