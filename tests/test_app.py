"""The FastAPI app over real WebSockets (TestClient), wired by the composition root."""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())  # fresh in-memory state per test


@contextmanager
def player(client: TestClient, player_id: int):
    """Connect as a player and consume the initial preferences message."""
    with client.websocket_connect(f"/ws/{player_id}") as ws:
        assert ws.receive_json() == {
            "type": "preferences",
            "data": {"player_id": player_id, "enabled": {"game": True, "social": True}},
        }
        yield ws


def test_health_and_dashboard_are_served(client):
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert "Gaming Notification Service" in response.text


def test_attack_reaches_defender_and_not_attacker(client):
    with player(client, 1) as p1, player(client, 2) as p2:
        p1.send_json({"action": "attack", "target_id": 2})
        assert p1.receive_json() == {"type": "ack", "action": "attack"}

        received = p2.receive_json()
        assert received["type"] == "notification"
        assert received["data"]["message"] == "Player '1' has attacked you!"

        # The attacker's next message is this level-up, so no attack notification
        # was delivered to them in between.
        p1.send_json({"action": "level_up", "level": 2})
        assert p1.receive_json()["data"]["event_type"] == "level_up"


def test_friend_request_accept_round_trip(client):
    with player(client, 1) as p1, player(client, 2) as p2:
        p1.send_json({"action": "send_friend_request", "target_id": 2})
        p1.receive_json()  # ack
        request = p2.receive_json()["data"]
        assert request["actor_id"] == 1

        p2.send_json({"action": "accept_friend_request", "target_id": request["actor_id"]})
        p2.receive_json()  # ack
        accepted = p1.receive_json()["data"]
        assert accepted["message"] == "Player '2' accepted your friend request."


def test_preference_toggle_suppresses_social_but_not_game(client):
    with player(client, 1) as p1, player(client, 2) as p2:
        p2.send_json({"action": "set_preference", "category": "social", "enabled": False})
        assert p2.receive_json()["data"]["enabled"] == {"game": True, "social": False}

        p1.send_json({"action": "follow", "target_id": 2})
        p1.receive_json()
        p1.send_json({"action": "attack", "target_id": 2})
        p1.receive_json()

        # The follow was suppressed, so the attack is the next thing player 2 sees.
        assert p2.receive_json()["data"]["event_type"] == "pvp_attacked"


@pytest.mark.parametrize(
    ("raw", "expected_error"),
    [
        ("not json", "Invalid JSON"),
        ("[1, 2]", "Expected a JSON object"),
        ('{"action": "dance"}', "Unknown action: 'dance'"),
        ('{"action": "attack"}', "Missing field: target_id"),
        ('{"action": "attack", "target_id": 1}', "must be different players"),
        ('{"action": "level_up", "level": 0}', "greater than 0"),
        ('{"action": "set_preference", "category": "social", "enabled": "no"}', "true or false"),
        ('{"action": "set_preference", "category": "email", "enabled": true}', "email"),
    ],
)
def test_invalid_input_returns_error_and_keeps_socket_open(client, raw, expected_error):
    with player(client, 1) as p1:
        p1.send_text(raw)
        reply = p1.receive_json()
        assert reply["type"] == "error"
        assert expected_error in reply["message"]

        p1.send_json({"action": "level_up", "level": 2})
        assert p1.receive_json()["type"] == "notification"


def test_actor_is_taken_from_the_connection_not_the_payload(client):
    with player(client, 2) as p2, player(client, 3) as p3:
        # Player 3 tries to pose as player 1; the extra field is ignored.
        p3.send_json({"action": "attack", "target_id": 2, "attacker_id": 1})
        p3.receive_json()
        assert p2.receive_json()["data"]["actor_id"] == 3
