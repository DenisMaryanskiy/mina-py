import asyncio
from datetime import datetime, timezone

from fastapi import WebSocket

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.websocket import connection_manager

settings = get_settings()
logger = get_logger()


async def handle_websocket_message(
    message: dict, user_id: str, connection_id: str, websocket: WebSocket
):
    """
    Handle incoming WebSocket messages based on type.

    Args:
        message: Parsed message dict
        user_id: User ID
        connection_id: Connection ID
        websocket: WebSocket connection
    """
    message_type = message.get("type")

    if message_type == "ping":
        # Handle heartbeat
        await handle_ping(connection_id, message)

    elif message_type == "typing":
        # Handle typing indicator
        await handle_typing(user_id, message)

    elif message_type == "message":
        # Handle chat message (will be implemented in next phase)
        await handle_chat_message(user_id, message)

    elif message_type == "read_receipt":
        # Handle read receipt (will be implemented in next phase)
        await handle_read_receipt(user_id, message)

    else:
        logger.warning(f"Unknown message type from {user_id}: {message_type}")
        await connection_manager.send_personal_message(
            connection_id,
            {
                "type": "error",
                "error": f"Unknown message type: {message_type}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


async def handle_ping(connection_id: str, message: dict):
    """
    Handle ping/heartbeat message.

    :param connection_id: Connection ID
    :param message: Ping message
    """
    await connection_manager.update_heartbeat(connection_id)

    await connection_manager.send_personal_message(
        connection_id,
        {
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_timestamp": message.get("timestamp"),
        },
    )


async def handle_typing(user_id: str, message: dict):
    """
    Handle typing indicator message.

    :param user_id: User ID
    :param message: Typing message with conversation_id and is_typing
    """
    conversation_id = message.get("conversation_id")
    is_typing = message.get("is_typing", False)

    if not conversation_id:
        logger.warning(
            f"Typing indicator without conversation_id from {user_id}"
        )
        return

    await connection_manager.set_typing_status(
        conversation_id, user_id, is_typing
    )


async def handle_chat_message(user_id: str, message: dict):
    """
    Handle chat message.

    :param user_id: Sender user ID
    :param message: Message data
    """
    logger.info(f"Chat message from {user_id}: {message}")

    # TODO: Validate message
    # TODO: Save to database
    # TODO: Broadcast to conversation participants
    # TODO: Queue notification task


async def handle_read_receipt(user_id: str, message: dict):
    """
    Handle read receipt.

    :param user_id: User ID
    :param message: Read receipt data with message_id
    """
    logger.info(f"Read receipt from {user_id}: {message}")

    # TODO: Update message read status in database
    # TODO: Broadcast read receipt to sender


async def heartbeat_checker(user_id: str):
    """
    Periodic task to check for stale connections.

    :param user_id: User ID
    """
    try:
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)

            await connection_manager.check_stale_connections(
                timeout_seconds=settings.WS_HEARTBEAT_TIMEOUT
            )

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in heartbeat checker for {user_id}: {e}")
