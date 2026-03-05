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


@pytest.mark.asyncio
async def test_set_user_away_updates_redis_and_broadcasts(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    await connection_manager.set_user_away(test_user_id)

    hset_calls = [str(c) for c in mock_redis.hset.call_args_list]
    assert any("away" in c for c in hset_calls)

    mock_redis.publish.assert_called_once()
    _, payload = mock_redis.publish.call_args.args
    assert payload["type"] == "presence_update"
    assert payload["status"] == "away"
    assert payload["user_id"] == test_user_id


@pytest.mark.asyncio
async def test_get_bulk_presence_returns_all_users(
    connection_manager: ConnectionManager, mock_redis: AsyncMock
):
    user_ids = ["user-1", "user-2", "user-3"]

    # Simulate: user-1 online, others missing
    def hgetall_side_effect(key: str):
        if "user-1" in key:
            return {"status": "online", "last_seen": "2026-02-15T10:00:00Z"}
        return {}

    mock_redis.hgetall.side_effect = hgetall_side_effect

    results = await connection_manager.get_bulk_presence(user_ids)

    assert len(results) == 3
    assert results[0]["user_id"] == "user-1"
    assert results[0]["status"] == "online"
    assert results[1]["status"] == "offline"
    assert results[2]["status"] == "offline"
