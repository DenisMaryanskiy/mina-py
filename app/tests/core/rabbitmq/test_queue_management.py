from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rabbitmq import RabbitMQClient


@pytest.mark.asyncio
async def test_get_queue_size(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    mock_queue.declaration_result.message_count = 42
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    result = await rabbitmq_client_instance.get_queue_size("test_queue")

    assert result == 42


@pytest.mark.asyncio
async def test_get_queue_size_nonexistent_queue(
    rabbitmq_client_instance: RabbitMQClient,
):
    result = await rabbitmq_client_instance.get_queue_size("nonexistent")

    assert result == 0


@pytest.mark.asyncio
async def test_get_queue_size_error(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    mock_queue.declaration_result = MagicMock()
    type(mock_queue.declaration_result).message_count = property(
        lambda self: (_ for _ in ()).throw(Exception("Error"))
    )
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    result = await rabbitmq_client_instance.get_queue_size("test_queue")

    assert result == 0


@pytest.mark.asyncio
async def test_purge_queue(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    mock_queue.purge = AsyncMock(return_value=10)
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    result = await rabbitmq_client_instance.purge_queue("test_queue")

    assert result == 10
    mock_queue.purge.assert_called_once()


@pytest.mark.asyncio
async def test_purge_queue_nonexistent(rabbitmq_client_instance: RabbitMQClient):
    result = await rabbitmq_client_instance.purge_queue("nonexistent")

    assert result == 0


@pytest.mark.asyncio
async def test_purge_queue_error(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    mock_queue.purge = AsyncMock(side_effect=Exception("Purge failed"))
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    result = await rabbitmq_client_instance.purge_queue("test_queue")

    assert result == 0
