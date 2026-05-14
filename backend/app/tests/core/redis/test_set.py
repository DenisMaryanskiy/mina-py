from unittest.mock import AsyncMock

import pytest

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_sadd_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.sadd = AsyncMock(return_value=1)

    result = await redis_client_instance.sadd("test_key", "test_value")

    assert result == 1
    mock_redis_conn.sadd.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_sadd_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.sadd = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.sadd("test_key", "test_value")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_srem_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.srem = AsyncMock(return_value=1)

    result = await redis_client_instance.srem("test_key", "test_value")

    assert result == 1
    mock_redis_conn.srem.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_srem_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.srem = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.srem("test_key", "test_value")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_smembers_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.smembers = AsyncMock(return_value=set("test_value"))

    result = await redis_client_instance.smembers("test_key")

    assert result == set("test_value")
    mock_redis_conn.smembers.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_smembers_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.smembers = AsyncMock(
        side_effect=Exception("Connection lost")
    )

    result = await redis_client_instance.smembers("test_key")

    assert result == set()
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_sismember_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.sismember = AsyncMock(return_value=True)

    result = await redis_client_instance.sismember("test_key", "test_value")

    assert result is True
    mock_redis_conn.sismember.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_sismember_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.sismember = AsyncMock(
        side_effect=Exception("Connection lost")
    )

    result = await redis_client_instance.sismember("test_key", "test_value")

    assert result is False
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_sismember_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.sismember("test_key", "test_value")

    assert result is False
