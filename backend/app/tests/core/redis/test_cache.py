from unittest.mock import AsyncMock

import pytest

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_get_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.get = AsyncMock(return_value="test_value")

    result = await redis_client_instance.get("test_key")

    assert result == "test_value"
    mock_redis_conn.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_get_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.get = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.get("test_key")

    assert result is None
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_get_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.get("test_key")

    assert result is None


@pytest.mark.asyncio
async def test_set_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.set = AsyncMock(return_value=True)

    result = await redis_client_instance.set("test_key", "test_value")

    assert result is True
    mock_redis_conn.set.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_set_with_ttl(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.setex = AsyncMock(return_value=True)

    result = await redis_client_instance.set("test_key", "test_value", 5)

    assert result is True
    mock_redis_conn.setex.assert_called_once_with("test_key", 5, "test_value")


@pytest.mark.asyncio
async def test_set_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.set = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.set("test_key", "test_value")

    assert result is False
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_set_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.set("test_key", "test_value")

    assert result is False


@pytest.mark.asyncio
async def test_delete_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.delete = AsyncMock(return_value=1)

    result = await redis_client_instance.delete("test_key")

    assert result == 1
    mock_redis_conn.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_delete_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.delete = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.delete("test_key")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_delete_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.delete("test_key")

    assert result == 0


@pytest.mark.asyncio
async def test_exists_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.exists = AsyncMock(return_value=1)

    result = await redis_client_instance.exists("test_key")

    assert result == 1
    mock_redis_conn.exists.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_exists_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.exists = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.exists("test_key")

    assert result == 0
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_exists_when_not_connected():
    client = RedisClient()
    # redis is None

    result = await client.exists("test_key")

    assert result == 0


@pytest.mark.asyncio
async def test_expire_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.expire = AsyncMock(return_value=True)

    result = await redis_client_instance.expire("test_key", 5)

    assert result is True
    mock_redis_conn.expire.assert_called_once_with("test_key", 5)


@pytest.mark.asyncio
async def test_expire_error(
    redis_client_instance: RedisClient,
    mock_redis_conn: AsyncMock,
    mock_logger: AsyncMock,
):
    mock_redis_conn.expire = AsyncMock(side_effect=Exception("Connection lost"))

    result = await redis_client_instance.expire("test_key", 5)

    assert result is False
    assert mock_logger.error.called
