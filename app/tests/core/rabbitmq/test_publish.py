import json
from unittest.mock import AsyncMock

import pytest
from aio_pika import DeliveryMode

from app.core.rabbitmq import RabbitMQClient


@pytest.mark.asyncio
async def test_publish_string_message(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    result = await rabbitmq_client_instance.publish("test_queue", "test message")

    assert result is True

    mock_channel.default_exchange.publish.assert_called_once()

    call_args = mock_channel.default_exchange.publish.call_args
    message = call_args[0][0]
    assert message.body == b"test message"
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    assert message.content_type == "application/json"


@pytest.mark.asyncio
async def test_publish_dict_message(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    test_data = {"key": "value", "number": 42}
    result = await rabbitmq_client_instance.publish("test_queue", test_data)

    assert result is True

    call_args = mock_channel.default_exchange.publish.call_args
    message = call_args[0][0]
    decoded_body = json.loads(message.body.decode())
    assert decoded_body == test_data


@pytest.mark.asyncio
async def test_publish_auto_declares_queue(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
    mock_channel.declare_exchange = AsyncMock()

    result = await rabbitmq_client_instance.publish("new_queue", "test message")

    assert result is True

    mock_channel.declare_queue.assert_called()
    assert "new_queue" in rabbitmq_client_instance.queues


@pytest.mark.asyncio
async def test_publish_without_channel(mock_logger: AsyncMock):
    client = RabbitMQClient(logger=mock_logger)
    # channel is None

    result = await client.publish("test_queue", "message")

    assert result is False
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_publish_error(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
    mock_logger: AsyncMock,
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    mock_channel.default_exchange.publish = AsyncMock(
        side_effect=Exception("Publish failed")
    )

    result = await rabbitmq_client_instance.publish("test_queue", "test message")

    assert result is False
    assert mock_logger.error.called
