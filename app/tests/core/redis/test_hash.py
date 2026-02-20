from unittest.mock import AsyncMock

import pytest

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_hget_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.hget = AsyncMock(return_value="test_value")

    result = await redis_client_instance.hget("test_name", "test_key")

    assert result == "test_value"
    mock_redis_conn.hget.assert_called_once_with("test_name", "test_key")


@pytest.mark.asyncio
async def test_hget_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.hget = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.hget("test_name", "test_key")

    assert result is None
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_hget_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.hget("test_name", "test_key")

    assert result is None


@pytest.mark.asyncio
async def test_hset_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.hset = AsyncMock(return_value=True)

    result = await redis_client_instance.hset(
        "test_name", "test_key", "test_value"
    )

    assert result is True
    mock_redis_conn.hset.assert_called_once_with(
        "test_name", "test_key", "test_value"
    )


@pytest.mark.asyncio
async def test_hset_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.hset = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.hset(
        "test_name", "test_key", "test_value"
    )

    assert result is False
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_hgetall_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.hgetall = AsyncMock(return_value={"test_key": "test_value"})

    result = await redis_client_instance.hgetall("test_name")

    assert result == {"test_key": "test_value"}
    mock_redis_conn.hgetall.assert_called_once_with("test_name")


@pytest.mark.asyncio
async def test_hgetall_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.hgetall = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.hgetall("test_name")

    assert result == {}
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_hgetall_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.hgetall("test_name")

    assert result == {}


@pytest.mark.asyncio
async def test_hdel_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.hdel = AsyncMock(return_value=1)

    result = await redis_client_instance.hdel("test_name", "test_key")

    assert result == 1
    mock_redis_conn.hdel.assert_called_once_with("test_name", "test_key")


@pytest.mark.asyncio
async def test_hdel_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.hdel = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.hdel("test_name", "test_key")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_hdel_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.hdel("test_name", "test_key")

    assert result == 0
