from unittest.mock import AsyncMock

import pytest

from app.core.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_connect_and_disconnect(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()

    connection_id = await connection_manager.connect(websocket, test_user_id)

    assert connection_id in connection_manager.active_connections
    assert connection_id in connection_manager.heartbeat
    websocket.accept.assert_called_once()

    mock_redis.sadd.assert_called()
    mock_redis.hset.assert_called()
    mock_redis.expire.assert_called()
    mock_redis.publish.assert_called()

    await connection_manager.disconnect(connection_id, test_user_id)

    assert connection_id not in connection_manager.active_connections
    assert connection_id not in connection_manager.heartbeat

    mock_redis.srem.assert_called()
