"""NotificationRouter: the core pipeline from event to delivered notification."""

from __future__ import annotations

import logging
from typing import Mapping, Optional

from src.domain.events import BaseEvent
from src.ports.event_bus import IEventBus
from src.ports.notification_channel import INotificationChannel
from src.ports.preference_repository import IPreferenceRepository
from src.services.formatters import DEFAULT_FORMATTERS, Formatter

logger = logging.getLogger(__name__)


class NotificationRouter:
    """Event -> format (Strategy) -> check preferences -> send (Adapter).

    The router depends only on ports, so every collaborator can be swapped
    (a broker for the bus, a database for preferences, push or email for the
    channel) without changing this class.
    """

    def __init__(
        self,
        preferences: IPreferenceRepository,
        channel: INotificationChannel,
        formatters: Optional[Mapping[type[BaseEvent], Formatter]] = None,
    ) -> None:
        self._preferences = preferences
        self._channel = channel
        self._formatters = dict(DEFAULT_FORMATTERS if formatters is None else formatters)

    def subscribe_to(self, bus: IEventBus) -> None:
        """Listen for every event type that has a formatting strategy."""
        for event_type in self._formatters:
            bus.subscribe(event_type, self.handle)

    async def handle(self, event: BaseEvent) -> None:
        formatter = self._formatters.get(type(event))
        if formatter is None:
            logger.warning("No formatter registered for %s", type(event).__name__)
            return

        notification = formatter(event)
        if notification is None:
            logger.debug("%s produced no notification", type(event).__name__)
            return

        preferences = await self._preferences.get(notification.recipient_id)
        if not preferences.is_enabled(notification.category):
            logger.info(
                "Player %s opted out of %s; suppressing %s",
                notification.recipient_id,
                notification.category.value,
                notification.event_type,
            )
            return

        await self._channel.send(notification)
