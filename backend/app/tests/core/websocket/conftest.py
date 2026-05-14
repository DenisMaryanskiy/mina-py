from logging import Logger
from unittest.mock import AsyncMock

import pytest

from app.core.redis import RedisClient
from app.core.websocket import ConnectionManager


@pytest.fixture
def mock_logger() -> AsyncMock:
    mock = AsyncMock(spec=Logger)

    mock.error = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def mock_redis() -> AsyncMock:
    mock = AsyncMock(spec=RedisClient)

    mock.sadd = AsyncMock(return_value=1)
    mock.srem = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.hset = AsyncMock(return_value=1)
    mock.hget = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hdel = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def connection_manager(
    mock_logger: AsyncMock, mock_redis: AsyncMock
) -> ConnectionManager:
    return ConnectionManager(logger=mock_logger, redis=mock_redis)


@pytest.fixture
def mock_websocket() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def test_user_id() -> str:
    return "123e4567-e89b-12d3-a456-426614174000"
