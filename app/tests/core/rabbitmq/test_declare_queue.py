from unittest.mock import AsyncMock

import pytest
from aio_pika import ExchangeType
from aio_pika.abc import AbstractQueue

from app.core.rabbitmq import RabbitMQClient


@pytest.mark.asyncio
async def test_declare_queue_basic(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
    mock_channel.declare_exchange = AsyncMock()

    result = await rabbitmq_client_instance.declare_queue(
        "test_queue", durable=True, declare_dlq=False
    )

    assert result == mock_queue
    assert "test_queue" in rabbitmq_client_instance.queues

    mock_channel.declare_queue.assert_called_once_with(
        "test_queue", durable=True, arguments={}
    )


@pytest.mark.asyncio
async def test_declare_queue_without_channel():
    client = RabbitMQClient()

    with pytest.raises(RuntimeError, match="channel is not initialized"):
        await client.declare_queue("test_queue")


@pytest.mark.asyncio
async def test_declare_queue_with_dlq(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    mock_dlq = AsyncMock(spec=AbstractQueue)
    mock_dlq.bind = AsyncMock()

    mock_dlx = AsyncMock()

    mock_channel.declare_queue = AsyncMock(side_effect=[mock_dlq, mock_queue])
    mock_channel.declare_exchange = AsyncMock(return_value=mock_dlx)

    result = await rabbitmq_client_instance.declare_queue(
        "test_queue", durable=True, declare_dlq=True
    )

    assert result == mock_queue

    mock_channel.declare_exchange.assert_called_once_with(
        "test_queue.dlx", ExchangeType.DIRECT, durable=True
    )

    assert mock_channel.declare_queue.call_count == 2
    mock_dlq.bind.assert_called_once_with(mock_dlx, routing_key="test_queue")

    main_queue_call = mock_channel.declare_queue.call_args_list[1]
    queue_args = main_queue_call[1]['arguments']
    assert queue_args['x-dead-letter-exchange'] == "test_queue.dlx"
    assert queue_args['x-dead-letter-routing-key'] == "test_queue"
