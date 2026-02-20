import json
from unittest.mock import AsyncMock

import pytest

from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_get_json_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    test_data = {"key": "value", "number": 42}
    json_string = json.dumps(test_data)
    mock_redis_conn.get = AsyncMock(return_value=json_string)

    result = await redis_client_instance.get_json("test_key")

    assert result == test_data


@pytest.mark.asyncio
async def test_get_json_none(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.get = AsyncMock(return_value=None)

    result = await redis_client_instance.get_json("test_key")

    assert result is None


@pytest.mark.asyncio
async def test_get_json_error(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    mock_redis_conn.get = AsyncMock(return_value="not_valid_json{")

    result = await redis_client_instance.get_json("test_key")

    assert result is None


@pytest.mark.asyncio
async def test_set_json_success(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    test_data = {"key": "value", "list": [1, 2, 3]}
    mock_redis_conn.set = AsyncMock(return_value=True)

    result = await redis_client_instance.set_json("test_key", test_data)

    assert result is True

    call_args = mock_redis_conn.set.call_args
    stored_value = call_args[0][1]
    assert json.loads(stored_value) == test_data


@pytest.mark.asyncio
async def test_set_json_non_serializable(
    redis_client_instance: RedisClient, mock_redis_conn: AsyncMock
):
    class NonSerializable:
        self_ref: NonSerializable | None = None

    obj = NonSerializable()
    obj.self_ref = obj

    result = await redis_client_instance.set_json("test_key", obj)

    assert result is False
