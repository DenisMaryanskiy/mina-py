import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio.client import PubSub

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_publish_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.publish = AsyncMock(return_value=1)

    message = {"message": "test_message"}
    result = await redis_client_instance.publish("test_channel", message)

    assert result == 1
    mock_redis_conn.publish.assert_called_once_with(
        "test_channel", json.dumps(message)
    )


@pytest.mark.asyncio
async def test_publish_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.publish = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.publish("test_channel", "test_message")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_subscribe_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.subscribe = AsyncMock()
    mock_redis_conn.pubsub = MagicMock(return_value=mock_pubsub)

    await redis_client_instance.subscribe("channel1", "channel2")

    assert redis_client_instance.pubsub is not None

    mock_pubsub.subscribe.assert_called_once_with("channel1", "channel2")


@pytest.mark.asyncio
async def test_subscribe_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.subscribe = AsyncMock(side_effect=Exception("Connection lost"))
    mock_redis_conn.pubsub = MagicMock(return_value=mock_pubsub)

    result = await redis_client_instance.subscribe("channel1", "channel2")

    assert result is None
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_subscribe_when_not_connected():
    client = RedisClient()
    # Redis is none

    result = await client.subscribe("channel1", "channel2")

    assert result is None


@pytest.mark.asyncio
async def test_unsubscribe_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.unsubscribe = AsyncMock()
    redis_client_instance.pubsub = mock_pubsub

    await redis_client_instance.unsubscribe("channel1", "channel2")

    assert redis_client_instance.pubsub is not None

    mock_pubsub.unsubscribe.assert_called_once_with("channel1", "channel2")


@pytest.mark.asyncio
async def test_unsubscribe_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=Exception("Connection lost"))
    redis_client_instance.pubsub = mock_pubsub

    result = await redis_client_instance.unsubscribe("channel1", "channel2")

    assert result is None
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_get_message_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.get_message = AsyncMock(return_value={"message": "test_message"})
    redis_client_instance.pubsub = mock_pubsub

    result = await redis_client_instance.get_message()

    assert result == {"message": "test_message"}

    mock_pubsub.get_message.called


@pytest.mark.asyncio
async def test_get_message_no_pubsub(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    redis_client_instance.pubsub = None

    result = await redis_client_instance.get_message()

    assert result is None


@pytest.mark.asyncio
async def test_get_message_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.get_message = AsyncMock(side_effect=Exception("Connection lost"))
    redis_client_instance.pubsub = mock_pubsub

    result = await redis_client_instance.get_message()

    assert result is None
    assert mock_logger.error.called
