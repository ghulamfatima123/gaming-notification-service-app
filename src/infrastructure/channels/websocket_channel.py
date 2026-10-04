"""In-app delivery: pushes notifications to connected players over WebSockets."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

from src.domain.notification import Notification
from src.ports.notification_channel import INotificationChannel

logger = logging.getLogger(__name__)


class WebSocketChannel(INotificationChannel):
    """Adapter from INotificationChannel to live FastAPI WebSocket connections.

    - A player may have several open connections (e.g. multiple tabs). Every
      one of them receives the notification.
    - The HTTP endpoint owns the handshake (``accept``) and the receive loop.
      This class only tracks connections and delivers to them.
    - Offline players: the notification is dropped and logged. This is a
      deliberate tradeoff for the exercise. A persistent inbox that is replayed
      on connect is the natural extension point.
    """

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    def register(self, player_id: int, websocket: WebSocket) -> None:
        self._connections[player_id].add(websocket)
        logger.info(
            "Player %s connected (%d socket(s))",
            player_id,
            len(self._connections[player_id]),
        )

    def unregister(self, player_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(player_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            del self._connections[player_id]
        logger.info("Player %s disconnected", player_id)

    def is_online(self, player_id: int) -> bool:
        return bool(self._connections.get(player_id))

    async def send(self, notification: Notification) -> None:
        player_id = notification.recipient_id
        sockets = self._connections.get(player_id)
        if not sockets:
            logger.info(
                "Player %s offline; dropping %s notification %s",
                player_id,
                notification.event_type,
                notification.id,
            )
            return

        payload = {"type": "notification", "data": notification.model_dump(mode="json")}
        # Iterate over a snapshot: dead sockets are removed during the loop.
        for websocket in list(sockets):
            try:
                await websocket.send_json(payload)
            except Exception:  # connection closed or broken mid-send
                logger.warning("Dropping dead socket for player %s", player_id, exc_info=True)
                self.unregister(player_id, websocket)
