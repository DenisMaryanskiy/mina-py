import asyncio
import json
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, status

from app.api.websockets.messages import (
    handle_websocket_message,
    heartbeat_checker,
)
from app.api.websockets.router import ws_router
from app.core.config import get_settings
from app.core.dependencies import get_user_from_token_ws
from app.core.logger import get_logger
from app.core.websocket import connection_manager

logger = get_logger()
settings = get_settings()


@ws_router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.

    Connection Flow:
    1. Client connects with JWT token in query params: ws://host/ws?token=JWT_TOKEN
    2. Server validates token and accepts connection
    3. Client receives connection_established message
    4. Client must send heartbeat every 30 seconds
    5. Server broadcasts messages via Redis pub/sub

    Message Types:
    - ping: Heartbeat from client
    - pong: Heartbeat response from server
    - message: Chat message
    - typing: Typing indicator
    - presence: User presence update

    Example client connection:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws?token=${accessToken}`);
    ```
    """
    connection_id = None
    user_id = None

    try:
        # Authenticate user from token
        user_id = await get_user_from_token_ws(websocket)

        if not user_id:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication failed",
            )
            return

        # Accept connection and register user
        connection_id = await connection_manager.connect(websocket, user_id)

        # Start heartbeat checker task
        heartbeat_task = asyncio.create_task(heartbeat_checker(user_id))

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                await handle_websocket_message(
                    message, user_id, connection_id, websocket
                )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {user_id}")
                break

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from user {user_id}: {data}")
                await connection_manager.send_personal_message(
                    connection_id,
                    {
                        "type": "error",
                        "error": "Invalid JSON format",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            except Exception as e:
                logger.error(f"Error processing message from {user_id}: {e}")
                await connection_manager.send_personal_message(
                    connection_id,
                    {
                        "type": "error",
                        "error": "Internal server error",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    finally:
        if connection_id and user_id:
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            await connection_manager.disconnect(connection_id, user_id)
