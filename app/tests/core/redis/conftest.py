from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.redis import RedisClient


@pytest.fixture
def mock_logger() -> AsyncMock:
    mock = AsyncMock(spec=Logger)

    mock.error = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def mock_redis_conn() -> AsyncMock:
    mock = AsyncMock(spec=Redis)

    mock.ping = AsyncMock(return_value=True)
    mock.close = AsyncMock()

    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)

    mock.hget = AsyncMock(return_value=None)
    mock.hset = AsyncMock(return_value=1)
    mock.hgetall = AsyncMock(return_value={})
    mock.hdel = AsyncMock(return_value=1)

    mock.sadd = AsyncMock(return_value=1)
    mock.srem = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.sismember = AsyncMock(return_value=False)

    mock.publish = AsyncMock(return_value=1)
    mock.pubsub = MagicMock(return_value=AsyncMock(spec=PubSub))

    return mock


@pytest.fixture
def redis_client_instance(
    mock_redis_conn: AsyncMock, mock_logger: AsyncMock
) -> RedisClient:
    client = RedisClient()
    client.redis = mock_redis_conn
    client.logger = mock_logger
    return client
