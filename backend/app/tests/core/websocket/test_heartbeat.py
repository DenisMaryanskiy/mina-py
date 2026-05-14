import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_heartbeat_update(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()

    connection_id = await connection_manager.connect(websocket, test_user_id)

    initial_time = connection_manager.heartbeat[connection_id]

    await asyncio.sleep(0.1)

    result = await connection_manager.update_heartbeat(connection_id)

    assert result is True
    assert connection_manager.heartbeat[connection_id] > initial_time


@pytest.mark.asyncio
async def test_heartbeat_update_false(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()

    _ = await connection_manager.connect(websocket, test_user_id)

    result = await connection_manager.update_heartbeat(
        "non_existent_connection_id"
    )

    assert result is False


@pytest.mark.asyncio
async def test_check_stale_connections(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()

    connection_id = await connection_manager.connect(websocket, test_user_id)

    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    connection_manager.heartbeat[connection_id] = old_time

    await connection_manager.check_stale_connections(timeout_seconds=60)

    websocket.close.assert_called_once()

    assert connection_id not in connection_manager.active_connections
    assert connection_id not in connection_manager.heartbeat


@pytest.mark.asyncio
async def test_check_stale_connections_error(
    connection_manager: ConnectionManager,
    mock_logger: AsyncMock,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock(side_effect=Exception("Close failed!"))

    connection_id = await connection_manager.connect(websocket, test_user_id)

    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    connection_manager.heartbeat[connection_id] = old_time

    await connection_manager.check_stale_connections(timeout_seconds=60)

    assert connection_id not in connection_manager.active_connections
    assert connection_id not in connection_manager.heartbeat

    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_check_stale_marks_user_away(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_websocket: AsyncMock,
):
    user_id = "user-away"
    connection_id = "conn-away"

    connection_manager.active_connections[connection_id] = mock_websocket
    connection_manager.connection_user[connection_id] = user_id
    # Last heartbeat was 40 seconds ago (past 30-s away threshold)
    connection_manager.heartbeat[connection_id] = datetime.now(
        timezone.utc
    ) - timedelta(seconds=40)

    await connection_manager.check_stale_connections(
        timeout_seconds=60, away_threshold_seconds=30
    )

    # User should NOT be disconnected
    mock_websocket.close.assert_not_called()
    assert connection_id in connection_manager.active_connections

    # But must have received an "away" presence_update broadcast
    mock_redis.publish.assert_called()
    calls_payloads = [c.args[1] for c in mock_redis.publish.call_args_list]
    away_events = [
        p
        for p in calls_payloads
        if isinstance(p, dict) and p.get("status") == "away"
    ]
    assert len(away_events) == 1
