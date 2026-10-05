"""FastAPI entrypoint: WebSocket endpoint, dashboard and wiring.

Run with:  uvicorn main:app --reload
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from src.bootstrap import NotificationSystem, build_system
from src.domain import ItemRarity, NotificationCategory
from src.infrastructure.channels import WebSocketChannel

STATIC_DIR = Path(__file__).parent / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)


async def preferences_message(
    system: NotificationSystem, player_id: int
) -> dict[str, Any]:
    preferences = await system.preferences.get(player_id)
    return {"type": "preferences", "data": preferences.model_dump(mode="json")}


async def roster_message(system: NotificationSystem, channel: WebSocketChannel) -> dict[str, Any]:
    """Every player who is online or has notifications waiting, for the dashboard sidebar."""
    tabs = channel.connection_counts()
    waiting = await system.inbox.pending_counts()
    players = []
    for player_id in sorted(tabs.keys() | waiting.keys()):
        preferences = await system.preferences.get(player_id)
        players.append(
            {
                "player_id": player_id,
                "online": player_id in tabs,
                "tabs": tabs.get(player_id, 0),
                "waiting": waiting.get(player_id, 0),
                "preferences": preferences.model_dump(mode="json")["enabled"],
            }
        )
    return {"type": "roster", "data": players}


async def handle_action(
    system: NotificationSystem, player_id: int, message: dict[str, Any]
) -> dict[str, Any]:
    """Translate one dashboard action into a producer call (simulating the game).

    The acting player always comes from the connection, never from the
    payload, so a client can't act on another player's behalf.
    """
    game, social = system.game, system.social
    action = message.get("action")

    match action:
        case "level_up":
            await game.player_leveled_up(player_id, int(message["level"]))
        case "acquire_item":
            rarity = ItemRarity(message.get("rarity", ItemRarity.RARE.value))
            await game.item_acquired(player_id, str(message["item_name"]), rarity)
        case "complete_challenge":
            await game.challenge_completed(player_id, str(message["challenge_name"]))
        case "attack":
            await game.player_attacked(player_id, int(message["target_id"]))
        case "defeat":
            await game.player_defeated(player_id, int(message["target_id"]))
        case "send_friend_request":
            await social.friend_request_sent(player_id, int(message["target_id"]))
        case "accept_friend_request":
            await social.friend_request_accepted(player_id, int(message["target_id"]))
        case "follow":
            await social.new_follower(player_id, int(message["target_id"]))
        case "set_preference":
            enabled = message["enabled"]
            if not isinstance(enabled, bool):
                raise TypeError("'enabled' must be true or false")
            category = NotificationCategory(message["category"])
            current = await system.preferences.get(player_id)
            await system.preferences.set(current.with_category(category, enabled))
            return await preferences_message(system, player_id)
        case _:
            raise ValueError(f"Unknown action: {action!r}")

    return {"type": "ack", "action": action}


def describe_error(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "Invalid JSON"
    if isinstance(exc, ValidationError):
        return "; ".join(err["msg"] for err in exc.errors())
    if isinstance(exc, KeyError):
        return f"Missing field: {exc.args[0]}"
    return str(exc)


def create_app() -> FastAPI:
    channel = WebSocketChannel()
    system = build_system(channel)

    app = FastAPI(title="Gaming Notification Service")
    # Sockets that asked for roster updates ({"action": "watch_roster"}). Opt-in, so
    # clients that don't need presence see exactly the original protocol.
    roster_watchers: set[WebSocket] = set()

    async def broadcast_roster() -> None:
        if not roster_watchers:
            return
        message = await roster_message(system, channel)
        for watcher in list(roster_watchers):
            try:
                await watcher.send_json(message)
            except Exception:  # closed mid-send; its own handler cleans up
                roster_watchers.discard(watcher)

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws/{player_id}")
    async def player_socket(websocket: WebSocket, player_id: int) -> None:
        await websocket.accept()
        channel.register(player_id, websocket)
        console = logging.getLogger("websocket")
        console.info(f"Player {player_id} connected to WebSocket")
        try:
            await websocket.send_json(await preferences_message(system, player_id))
            missed = await system.inbox.drain(player_id)
            if missed:
                await websocket.send_json(
                    {"type": "missed", "data": [n.model_dump(mode="json") for n in missed]}
                )
            await broadcast_roster()
            while True:
                raw = await websocket.receive_text()
                reply: dict[str, Any]
                try:
                    message = json.loads(raw)
                    if not isinstance(message, dict):
                        raise ValueError("Expected a JSON object")
                    if message.get("action") == "watch_roster":
                        roster_watchers.add(websocket)
                        reply = await roster_message(system, channel)
                    else:
                        reply = await handle_action(system, player_id, message)
                except (KeyError, TypeError, ValueError) as exc:
                    # pydantic.ValidationError and JSONDecodeError are ValueErrors.
                    reply = {"type": "error", "message": describe_error(exc)}
                await websocket.send_json(reply)
                if reply["type"] in ("ack", "preferences"):
                    await broadcast_roster()  # inbox or preferences may have changed
        except WebSocketDisconnect:
            pass
        finally:
            channel.unregister(player_id, websocket)
            roster_watchers.discard(websocket)
            await broadcast_roster()

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
