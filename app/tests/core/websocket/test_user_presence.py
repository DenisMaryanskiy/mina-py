from unittest.mock import AsyncMock

import pytest

from app.core.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_user_presence(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    mock_redis.hgetall.return_value = {
        "status": "online",
        "last_seen": "2024-01-01",
    }

    await connection_manager.set_user_online(test_user_id)

    assert mock_redis.hset.called
    assert mock_redis.expire.called
    assert mock_redis.publish.called

    presence = await connection_manager.get_user_presence(test_user_id)
    assert presence["status"] == "online"

    await connection_manager.set_user_offline(test_user_id)
    assert mock_redis.hset.called


@pytest.mark.asyncio
async def test_get_user_presence_empty(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    presence = await connection_manager.get_user_presence(test_user_id)
    assert presence["status"] == "offline"
    assert presence["last_seen"] is None


@pytest.mark.asyncio
async def test_typing_status(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    conversation_id = "conv-123"

    await connection_manager.set_typing_status(
        conversation_id, test_user_id, is_typing=True
    )

    assert mock_redis.hset.called, "hset should be called for typing=True"
    assert mock_redis.expire.called, "expire should be called for typing=True"
    assert mock_redis.publish.called, "publish should be called for broadcast"

    mock_redis.hset.reset_mock()
    mock_redis.hdel.reset_mock()
    mock_redis.publish.reset_mock()

    await connection_manager.set_typing_status(
        conversation_id, test_user_id, is_typing=False
    )

    assert mock_redis.hdel.called, "hdel should be called for typing=False"
    assert mock_redis.publish.called, "publish should be called for broadcast"
