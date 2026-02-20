import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.core.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_start_pubsub_listener_subscribes_to_channel(
    connection_manager: ConnectionManager, mock_redis: AsyncMock
):
    await connection_manager.start_pubsub_listener()

    mock_redis.subscribe.assert_called_once_with("presence")

    assert connection_manager.pubsub_task is not None
    assert isinstance(connection_manager.pubsub_task, asyncio.Task)

    await connection_manager.stop_pubsub_listener()


@pytest.mark.asyncio
async def test_start_pubsub_listener_error(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis.subscribe = AsyncMock(side_effect=Exception("Subscribe failed!"))

    with pytest.raises(Exception):
        await connection_manager.start_pubsub_listener()
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_listener_loop_receives_and_processes_message(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_websocket: AsyncMock,
):

    message = {
        "type": "message",
        "channel": "presence",
        "data": json.dumps({"type": "user_online", "user_id": "user-123"}),
    }

    call_count = 0

    async def mock_get_message(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return message
        await asyncio.sleep(0.1)
        return None

    mock_redis.get_message = AsyncMock(side_effect=mock_get_message)

    _ = await connection_manager.connect(mock_websocket, "user-456")

    await connection_manager.start_pubsub_listener()

    await asyncio.sleep(0.15)

    await connection_manager.stop_pubsub_listener()

    assert mock_websocket.send_json.call_count >= 2

    calls = mock_websocket.send_json.call_args_list
    presence_calls = [
        call for call in calls if call[0][0].get("type") == "user_online"
    ]
    assert len(presence_calls) > 0


@pytest.mark.asyncio
async def test_listener_loop_handles_user_message(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_websocket: AsyncMock,
):
    user_id = "user-123"

    message = {
        "type": "message",
        "channel": f"user:{user_id}",
        "data": json.dumps(
            {"type": "notification", "content": "You have a new message"}
        ),
    }

    call_count = 0

    async def mock_get_message(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return message
        await asyncio.sleep(0.1)
        return None

    mock_redis.get_message = AsyncMock(side_effect=mock_get_message)

    mock_redis.smembers = AsyncMock(return_value={"conn-1"})

    _ = await connection_manager.connect(mock_websocket, user_id)

    connection_manager.active_connections["conn-1"] = mock_websocket

    await connection_manager.start_pubsub_listener()

    await asyncio.sleep(0.15)

    await connection_manager.stop_pubsub_listener()

    assert mock_redis.get_message.called
    assert mock_websocket.send_json.called


@pytest.mark.asyncio
async def test_listener_loop_handles_conversation_message(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_websocket: AsyncMock,
):
    message = {
        "type": "message",
        "channel": "conversation:conv-123",
        "data": json.dumps(
            {
                "message": {
                    "type": "chat_message",
                    "content": "Hello everyone!",
                },
                "exclude_user_id": "user-999",
            }
        ),
    }

    call_count = 0

    async def mock_get_message(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return message
        await asyncio.sleep(0.1)
        return None

    mock_redis.get_message = AsyncMock(side_effect=mock_get_message)

    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()

    _ = await connection_manager.connect(ws1, "user-1")
    _ = await connection_manager.connect(ws2, "user-2")

    await connection_manager.start_pubsub_listener()

    await asyncio.sleep(0.15)

    await connection_manager.stop_pubsub_listener()

    assert ws1.send_json.called
    assert ws2.send_json.called


@pytest.mark.asyncio
async def test_listener_loop_error(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    mock_logger: AsyncMock,
):
    call_count = 0

    async def mock_get_message_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Redis connection lost")
        await asyncio.sleep(0.1)
        return None

    mock_redis.get_message = AsyncMock(side_effect=mock_get_message_error)

    await connection_manager.start_pubsub_listener()
    await asyncio.sleep(1.2)
    await connection_manager.stop_pubsub_listener()
    assert mock_logger.error.called
