"""Delivery-channel adapters (implementations of INotificationChannel)."""

from src.infrastructure.channels.websocket_channel import WebSocketChannel

__all__ = ["WebSocketChannel"]
