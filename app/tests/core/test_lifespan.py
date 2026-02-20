from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from app.core.lifespan import lifespan


def make_lifespan_mocks(
    *,
    redis_connect_raises: Exception | None = None,
    rabbitmq_connect_raises: Exception | None = None,
    pubsub_raises: Exception | None = None,
    shutdown_raises: Exception | None = None,
):
    """
    Return a dict of AsyncMock objects that can be used to patch the three
    clients (redis_client, rabbitmq_client, connection_manager) used inside
    the lifespan.
    """
    redis = AsyncMock()
    redis.connect = AsyncMock(side_effect=redis_connect_raises)
    redis.disconnect = AsyncMock(side_effect=shutdown_raises)

    rabbitmq = AsyncMock()
    rabbitmq.connect = AsyncMock(side_effect=rabbitmq_connect_raises)
    rabbitmq.declare_queue = AsyncMock()
    rabbitmq.disconnect = AsyncMock(side_effect=shutdown_raises)

    ws_manager = AsyncMock()
    ws_manager.start_pubsub_listener = AsyncMock(side_effect=pubsub_raises)
    ws_manager.stop_pubsub_listener = AsyncMock(side_effect=shutdown_raises)

    return redis, rabbitmq, ws_manager


@pytest.mark.asyncio
async def test_lifespan_startup_initialises_all_services(mock_logger: AsyncMock):
    redis, rabbitmq, ws_manager = make_lifespan_mocks()

    with (
        patch("app.core.lifespan.redis_client", redis),
        patch("app.core.lifespan.rabbitmq_client", rabbitmq),
        patch("app.core.lifespan.connection_manager", ws_manager),
        patch("app.core.lifespan.logger", mock_logger),
    ):
        app = FastAPI(lifespan=lifespan)

        @asynccontextmanager
        async def _run():
            async with lifespan(app):
                yield

        async with _run():
            redis.connect.assert_awaited_once()
            rabbitmq.connect.assert_awaited_once()
            ws_manager.start_pubsub_listener.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_raises_when_redis_connect_fails(mock_logger):
    error = ConnectionError("Redis unavailable")
    redis, rabbitmq, ws_manager = make_lifespan_mocks(redis_connect_raises=error)

    with (
        patch("app.core.lifespan.redis_client", redis),
        patch("app.core.lifespan.rabbitmq_client", rabbitmq),
        patch("app.core.lifespan.connection_manager", ws_manager),
        patch("app.core.lifespan.logger", mock_logger),
    ):
        app = FastAPI(lifespan=lifespan)

        with pytest.raises(ConnectionError, match="Redis unavailable"):
            async with lifespan(app):
                pass  # pragma: no cover


@pytest.mark.asyncio
async def test_lifespan_shutdown_error_is_logged_not_raised(mock_logger):
    redis, rabbitmq, ws_manager = make_lifespan_mocks(
        shutdown_raises=RuntimeError("teardown boom")
    )

    with (
        patch("app.core.lifespan.redis_client", redis),
        patch("app.core.lifespan.rabbitmq_client", rabbitmq),
        patch("app.core.lifespan.connection_manager", ws_manager),
        patch("app.core.lifespan.logger", mock_logger),
    ):
        app = FastAPI(lifespan=lifespan)

        # Should NOT raise even though shutdown fails
        async with lifespan(app):
            pass

        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert "shutdown" in error_msg.lower() or "teardown boom" in error_msg
