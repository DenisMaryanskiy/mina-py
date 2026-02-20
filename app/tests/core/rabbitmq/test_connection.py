from unittest.mock import AsyncMock

import pytest
from aio_pika.abc import AbstractChannel, AbstractConnection

from app.core.rabbitmq import (
    RabbitMQClient,
    get_rabbitmq_client,
    rabbitmq_client,
)


@pytest.mark.asyncio
async def test_connect_success(monkeypatch: pytest.MonkeyPatch):
    mock_connection = AsyncMock(spec=AbstractConnection)
    mock_channel = AsyncMock(spec=AbstractChannel)
    mock_channel.set_qos = AsyncMock()
    mock_connection.channel = AsyncMock(return_value=mock_channel)

    async def mock_connect_robust(url):
        return mock_connection

    monkeypatch.setattr("aio_pika.connect_robust", mock_connect_robust)

    client = RabbitMQClient()
    await client.connect()

    assert client.connection is not None
    assert client.channel is not None

    mock_channel.set_qos.assert_called_once_with(prefetch_count=1)


@pytest.mark.asyncio
async def test_connect_error(
    monkeypatch: pytest.MonkeyPatch, mock_logger: AsyncMock
):
    mock_connection = AsyncMock(spec=AbstractConnection)
    mock_channel = AsyncMock(spec=AbstractChannel)
    mock_channel.set_qos = AsyncMock()
    mock_connection.channel = AsyncMock(return_value=mock_channel)

    async def mock_connect_robust(url):
        raise Exception

    monkeypatch.setattr("aio_pika.connect_robust", mock_connect_robust)

    client = RabbitMQClient()

    with pytest.raises(Exception):
        await client.connect()
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_disconnect(
    rabbitmq_client_instance: RabbitMQClient,
    mock_connection: AsyncMock,
    mock_channel: AsyncMock,
):
    await rabbitmq_client_instance.disconnect()

    mock_channel.close.assert_called_once()
    mock_connection.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_rabbitmq_client_returns_global_instance():
    result = await get_rabbitmq_client()

    assert result is rabbitmq_client
    assert isinstance(result, RabbitMQClient)
