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
