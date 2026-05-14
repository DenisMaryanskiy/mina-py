from unittest.mock import AsyncMock

import pytest

from app.core.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_send_personal_message(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()

    connection_id = await connection_manager.connect(websocket, test_user_id)

    websocket.send_json.reset_mock()

    test_message = {"type": "test", "data": "hello"}
    await connection_manager.send_personal_message(connection_id, test_message)

    websocket.send_json.assert_called_once_with(test_message)


@pytest.mark.asyncio
async def test_send_personal_message_error(
    connection_manager: ConnectionManager,
    mock_logger: AsyncMock,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock(side_effect=Exception("Send JSON failed!"))

    connection_id = await connection_manager.connect(websocket, test_user_id)

    websocket.send_json.reset_mock()

    test_message = {"type": "test", "data": "hello"}
    await connection_manager.send_personal_message(connection_id, test_message)

    websocket.send_json.assert_called_once_with(test_message)

    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_send_to_user(
    connection_manager: ConnectionManager,
    mock_redis: AsyncMock,
    test_user_id: str,
):
    test_message = {"type": "test", "data": "hello"}
    await connection_manager.send_to_user(test_user_id, test_message)

    assert mock_redis.publish.called
