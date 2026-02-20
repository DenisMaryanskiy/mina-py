import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.websockets.endpoint import websocket_endpoint
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


@pytest.mark.asyncio
async def test_endpoint_inner_exception_sends_error_message(test_token):
    client = TestClient(app)

    with (
        patch("app.core.redis.redis_client"),
        patch(
            "app.api.websockets.endpoint.handle_websocket_message",
            side_effect=Exception("unexpected processing error"),
        ),
    ):
        with client.websocket_connect(
            f"/api/v1/ws?token={test_token}"
        ) as websocket:
            websocket.receive_json()  # consume connection_established

            websocket.send_json({"type": "ping"})

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert response["error"] == "Internal server error"
            assert "timestamp" in response


def make_mock_websocket(user_id: str = "user-1") -> MagicMock:
    """
    Build a minimal WebSocket mock that looks authenticated and yields one
    WebSocketDisconnect on the first receive_text call (so the loop exits
    cleanly after one iteration).
    """
    from fastapi import WebSocketDisconnect

    ws = MagicMock()
    ws.query_params = MagicMock()
    ws.query_params.get = MagicMock(return_value="valid-token")
    ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_outer_except_logs_connection_error():
    ws = make_mock_websocket()
    error = RuntimeError("broker unreachable")

    with (
        patch(
            "app.api.websockets.endpoint.get_user_from_token_ws",
            new=AsyncMock(return_value="user-1"),
        ),
        patch(
            "app.api.websockets.endpoint.connection_manager.connect",
            new=AsyncMock(side_effect=error),
        ),
        patch("app.api.websockets.endpoint.logger") as mock_logger,
        # disconnect is in finally — must not raise
        patch(
            "app.api.websockets.endpoint.connection_manager.disconnect",
            new=AsyncMock(),
        ),
    ):
        # Should complete without raising (outer except swallows the error)
        await websocket_endpoint(ws)

    mock_logger.error.assert_called_once()
    logged = str(mock_logger.error.call_args)
    assert "WebSocket connection error" in logged
    assert "broker unreachable" in logged


@pytest.mark.asyncio
async def test_finally_cancels_heartbeat_task_and_swallows_cancelled_error():
    ws = make_mock_websocket()

    async def endless_heartbeat(_user_id: str):
        """Simulates the real heartbeat_checker: loops until cancelled."""
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise  # let the Task machinery handle it

    with (
        patch(
            "app.api.websockets.endpoint.get_user_from_token_ws",
            new=AsyncMock(return_value="user-1"),
        ),
        patch(
            "app.api.websockets.endpoint.connection_manager.connect",
            new=AsyncMock(return_value="conn-1"),
        ),
        patch(
            "app.api.websockets.endpoint.connection_manager.send_personal_message",
            new=AsyncMock(),
        ),
        patch(
            "app.api.websockets.endpoint.connection_manager.disconnect",
            new=AsyncMock(),
        ),
        patch(
            "app.api.websockets.endpoint.heartbeat_checker",
            new=endless_heartbeat,
        ),
        patch("app.api.websockets.endpoint.logger"),
    ):
        await websocket_endpoint(ws)
