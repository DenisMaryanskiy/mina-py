from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_websocket_without_token():
    client = TestClient(app)

    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws"):
            pass


def test_websocket_with_invalid_token():
    client = TestClient(app)

    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws?token=invalid_token"):
            pass


@pytest.mark.asyncio
async def test_websocket_ping_pong(test_token):
    client = TestClient(app)

    with patch("app.core.redis.redis_client"):
        with client.websocket_connect(
            f"/api/v1/ws?token={test_token}"
        ) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection_established"

            websocket.send_json({"type": "ping", "timestamp": "2024-01-01"})

            data = websocket.receive_json()
            assert data["type"] == "pong"
            assert "timestamp" in data


@pytest.mark.asyncio
async def test_websocket_typing_indicator(test_token):
    client = TestClient(app)

    with patch("app.core.redis.redis_client"):
        with client.websocket_connect(
            f"/api/v1/ws?token={test_token}"
        ) as websocket:
            websocket.receive_json()

            websocket.send_json(
                {
                    "type": "typing",
                    "conversation_id": "conv-123",
                    "is_typing": True,
                }
            )


@pytest.mark.asyncio
async def test_websocket_invalid_json(test_token):
    client = TestClient(app)

    with patch("app.core.redis.redis_client"):
        with client.websocket_connect(
            f"/api/v1/ws?token={test_token}"
        ) as websocket:
            websocket.receive_json()

            websocket.send_text("invalid json{")

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["error"]


@pytest.mark.asyncio
async def test_websocket_unknown_message_type(test_token):
    client = TestClient(app)

    with patch("app.core.redis.redis_client"):
        with client.websocket_connect(
            f"/api/v1/ws?token={test_token}"
        ) as websocket:
            websocket.receive_json()

            websocket.send_json({"type": "unknown_type", "data": "test"})

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Unknown message type" in data["error"]
