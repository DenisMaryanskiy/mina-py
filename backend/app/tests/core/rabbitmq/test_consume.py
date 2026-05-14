import json
from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rabbitmq import RabbitMQClient


@pytest.mark.asyncio
async def test_consume_success(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    callback = AsyncMock()

    await rabbitmq_client_instance.consume(
        "test_queue", callback, auto_ack=False
    )

    mock_queue.consume.assert_called_once()


@pytest.mark.asyncio
async def test_consume_auto_declares_queue(
    rabbitmq_client_instance: RabbitMQClient,
    mock_channel: AsyncMock,
    mock_queue: AsyncMock,
):
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
    mock_channel.declare_exchange = AsyncMock()

    callback = AsyncMock()

    await rabbitmq_client_instance.consume("new_queue", callback)

    mock_channel.declare_queue.assert_called()
    assert "new_queue" in rabbitmq_client_instance.queues


@pytest.mark.asyncio
async def test_consume_message_handler_processes_json(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    callback = AsyncMock()
    captured_handler = None

    async def capture_handler(handler):
        nonlocal captured_handler
        captured_handler = handler

    mock_queue.consume = AsyncMock(side_effect=capture_handler)

    await rabbitmq_client_instance.consume("test_queue", callback)

    assert captured_handler is not None

    mock_message = AsyncMock()
    mock_message.body = json.dumps({"key": "value"}).encode()
    mock_message.ack = AsyncMock()
    mock_message.reject = AsyncMock()
    mock_message.process = MagicMock()
    mock_message.process.return_value.__aenter__ = AsyncMock()
    mock_message.process.return_value.__aexit__ = AsyncMock()

    await captured_handler(mock_message)

    callback.assert_called_once_with({"key": "value"})

    mock_message.ack.assert_called_once()


@pytest.mark.asyncio
async def test_consume_message_handler_invalid_json(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    callback = AsyncMock()
    captured_handler: Callable | None = None

    async def capture_handler(handler: Callable):
        nonlocal captured_handler
        captured_handler = handler

    mock_queue.consume = AsyncMock(side_effect=capture_handler)

    await rabbitmq_client_instance.consume("test_queue", callback)

    mock_message = AsyncMock()
    mock_message.body = b"invalid json{"
    mock_message.ack = AsyncMock()
    mock_message.reject = AsyncMock()
    mock_message.process = MagicMock()
    mock_message.process.return_value.__aenter__ = AsyncMock()
    mock_message.process.return_value.__aexit__ = AsyncMock()

    await captured_handler(mock_message)  # type: ignore[misc]

    callback.assert_not_called()

    mock_message.reject.assert_called_once_with(requeue=False)


@pytest.mark.asyncio
async def test_consume_message_handler_callback_error(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    callback = AsyncMock(side_effect=ValueError("Processing error"))
    captured_handler = None

    async def capture_handler(handler):
        nonlocal captured_handler
        captured_handler = handler

    mock_queue.consume = AsyncMock(side_effect=capture_handler)

    await rabbitmq_client_instance.consume("test_queue", callback)

    mock_message = AsyncMock()
    mock_message.body = json.dumps({"data": "test"}).encode()
    mock_message.ack = AsyncMock()
    mock_message.reject = AsyncMock()
    mock_message.process = MagicMock()
    mock_message.process.return_value.__aenter__ = AsyncMock()
    mock_message.process.return_value.__aexit__ = AsyncMock()

    await captured_handler(mock_message)  # type: ignore[misc]

    callback.assert_called_once()

    mock_message.reject.assert_called_once_with(requeue=False)


@pytest.mark.asyncio
async def test_consume_error(
    rabbitmq_client_instance: RabbitMQClient, mock_queue: AsyncMock
):
    rabbitmq_client_instance.queues["test_queue"] = mock_queue

    mock_queue.consume = AsyncMock(side_effect=Exception("Consume failed"))

    callback = AsyncMock()

    with pytest.raises(Exception):
        await rabbitmq_client_instance.consume("test_queue", callback)
