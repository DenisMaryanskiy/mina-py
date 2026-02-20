import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.websockets.messages import (
    handle_chat_message,
    handle_read_receipt,
    handle_typing,
    handle_websocket_message,
    heartbeat_checker,
)


@pytest.mark.asyncio
async def test_handle_websocket_message_dispatches_to_chat_message():
    with patch(
        "app.api.websockets.messages.handle_chat_message"
    ) as mock_handler:
        mock_handler.return_value = None
        mock_handler.__call__ = AsyncMock(return_value=None)
        mock_handler.side_effect = None

        ws = MagicMock()
        await handle_websocket_message(
            {"type": "message", "content": "hello"},
            user_id="user-1",
            connection_id="conn-1",
            websocket=ws,
        )

        mock_handler.assert_awaited_once_with(
            "user-1", {"type": "message", "content": "hello"}
        )


@pytest.mark.asyncio
async def test_handle_chat_message_logs_info():
    with patch("app.api.websockets.messages.logger") as mock_logger:
        await handle_chat_message(
            user_id="user-42", message={"type": "message", "content": "hi"}
        )

    mock_logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_handle_websocket_message_dispatches_to_read_receipt():
    with patch(
        "app.api.websockets.messages.handle_read_receipt"
    ) as mock_handler:
        mock_handler.return_value = None
        mock_handler.side_effect = None

        ws = MagicMock()
        await handle_websocket_message(
            {"type": "read_receipt", "message_id": "msg-99"},
            user_id="user-1",
            connection_id="conn-1",
            websocket=ws,
        )

        mock_handler.assert_awaited_once_with(
            "user-1", {"type": "read_receipt", "message_id": "msg-99"}
        )


@pytest.mark.asyncio
async def test_handle_read_receipt_logs_info():
    with patch("app.api.websockets.messages.logger") as mock_logger:
        await handle_read_receipt(
            user_id="user-7",
            message={"type": "read_receipt", "message_id": "m1"},
        )

    mock_logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_handle_typing_returns_early_without_conversation_id():
    with (
        patch("app.api.websockets.messages.logger") as mock_logger,
        patch("app.api.websockets.messages.connection_manager"),
    ):
        await handle_typing(
            user_id="user-1",
            message={"type": "typing", "is_typing": True},  # no conversation_id
        )

    mock_logger.warning.assert_called_once()
    warning_text = str(mock_logger.warning.call_args)
    assert "conversation_id" in warning_text


@pytest.mark.asyncio
async def test_heartbeat_checker_calls_check_stale_connections():
    call_count = 0

    async def fake_check(timeout_seconds):
        nonlocal call_count
        call_count += 1
        # Cancel after first real call so the test exits
        raise asyncio.CancelledError()

    with (
        patch("app.api.websockets.messages.asyncio.sleep", return_value=None),
        patch(
            "app.api.websockets.messages.connection_manager.check_stale_connections",
            side_effect=fake_check,
        ),
    ):
        # CancelledError is swallowed by inner except
        await heartbeat_checker("user-1")

    assert call_count == 1


@pytest.mark.asyncio
async def test_heartbeat_checker_outer_except_logs_error():
    with (
        patch("app.api.websockets.messages.asyncio.sleep", return_value=None),
        patch(
            "app.api.websockets.messages.connection_manager.check_stale_connections",
            side_effect=Exception("stale check exploded"),
        ),
        patch("app.api.websockets.messages.logger") as mock_logger,
    ):
        await heartbeat_checker("user-99")

    mock_logger.error.assert_called_once()
    logged = str(mock_logger.error.call_args)
    assert "user-99" in logged
    assert "stale check exploded" in logged
