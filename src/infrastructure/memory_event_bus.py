"""In-process, asyncio-based implementation of IEventBus."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from src.domain.events import BaseEvent
from src.ports.event_bus import EventHandler, IEventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """Fan-out pub/sub keyed by event class.

    - Subscriptions match by ``isinstance``, so subscribing to ``BaseEvent``
      receives every event.
    - ``publish`` awaits all matching handlers concurrently. A failing handler
      is logged and isolated; it never affects other handlers or the publisher.
    - Delivery is at-most-once and in-process. A broker (Kafka, SNS/SQS, Redis
      Streams) would replace this adapter without touching the core.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[BaseEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[BaseEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: BaseEvent) -> None:
        handlers = [
            handler
            for subscribed_type, registered in self._handlers.items()
            if isinstance(event, subscribed_type)
            for handler in registered
        ]
        if not handlers:
            logger.debug("No subscribers for %s", type(event).__name__)
            return

        results = await asyncio.gather(
            *(handler(event) for handler in handlers), return_exceptions=True
        )
        for handler, result in zip(handlers, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(
                    "Handler %r failed for %s (event_id=%s)",
                    handler,
                    type(event).__name__,
                    event.event_id,
                    exc_info=result,
                )
