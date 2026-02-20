from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue

from app.core.rabbitmq import RabbitMQClient


@pytest.fixture
def mock_logger() -> AsyncMock:
    mock = AsyncMock(spec=Logger)

    mock.error = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def mock_connection() -> AsyncMock:
    mock = AsyncMock(spec=AbstractConnection)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_channel() -> AsyncMock:
    mock = AsyncMock(spec=AbstractChannel)
    mock.close = AsyncMock()
    mock.set_qos = AsyncMock()
    mock.declare_exchange = AsyncMock()
    mock.declare_queue = AsyncMock()

    mock.default_exchange = AsyncMock()
    mock.default_exchange.publish = AsyncMock()

    return mock


@pytest.fixture
def mock_queue() -> AsyncMock:
    """Create a mock RabbitMQ queue."""
    mock = AsyncMock(spec=AbstractQueue)
    mock.bind = AsyncMock()
    mock.consume = AsyncMock()
    mock.purge = AsyncMock(return_value=0)

    mock.declaration_result = MagicMock()
    mock.declaration_result.message_count = 0

    return mock


@pytest.fixture
def rabbitmq_client_instance(
    mock_connection: AsyncMock, mock_channel: AsyncMock, mock_logger: AsyncMock
) -> RabbitMQClient:
    client = RabbitMQClient()
    client.logger = mock_logger
    client.connection = mock_connection
    client.channel = mock_channel
    return client
