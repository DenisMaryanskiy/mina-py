from unittest.mock import AsyncMock, patch

import pytest
from redis.asyncio import Redis

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_connect_success():
    client = RedisClient()

    with patch("redis.asyncio.Redis") as mock_redis_class:
        mock_instance = AsyncMock(spec=Redis)
        mock_instance.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_instance

        await client.connect()

        assert client.redis is not None
        mock_instance.ping.assert_called_once()


@pytest.mark.asyncio
async def test_connect_error(mock_logger: AsyncMock):
    client = RedisClient()

    with patch("redis.asyncio.Redis") as mock_redis_class:
        mock_instance = AsyncMock(spec=Redis)
        mock_instance.ping = AsyncMock(
            side_effect=Exception("Connection failed!")
        )
        mock_redis_class.return_value = mock_instance

        with pytest.raises(Exception):
            await client.connect()
            assert mock_logger.error.called


@pytest.mark.asyncio
async def test_disconnect(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    await redis_client_instance.disconnect()

    mock_redis_conn.close.assert_called_once()
