import asyncio
import json
import uuid
from datetime import datetime, timezone
from logging import Logger
from typing import Any

from fastapi import WebSocket

from app.core.logger import get_logger
from app.core.redis import RedisClient, get_redis


class ConnectionManager:
    """
    Websocket connection manager with Redis pub/sub for multi-server support.

    This manager handles:
    - WebSocket connections with heartbeat/ping-pong
    - User presence tracking
    - Message broadcasting via Redis pub/sub
    - Connection state management
    """

    def __init__(
        self, logger: Logger | None = None, redis: RedisClient | None = None
    ):
        self.logger = logger or get_logger()
        self.redis = redis or get_redis()

        # Local connections on this server instance
        self.active_connections: dict[str, WebSocket] = {}

        # Heartbeat tracking {connection_id: last_heartbeat_time}
        self.heartbeat: dict[str, datetime] = {}

        # Redis pub/sub for cross-server communication
        self.pubsub_task: asyncio.Task | None = None

    # ================ Connection management ================

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str | None = None,
    ) -> str:
        """
        Accept websocket connection and register user

        :param websocket: Websocket connection
        :param user_id: User ID from JWT token
        :param connection_id: Optional connection ID (generated if not provided)

        :return: Connection ID
        """
        await websocket.accept()

        # Generate unique connection_id
        if not connection_id:
            connection_id = str(uuid.uuid4())

        # Store connections locally
        self.active_connections[connection_id] = websocket
        self.heartbeat[connection_id] = datetime.now(timezone.utc)

        # Track connection in Redis
        await self._add_user_connection(user_id, connection_id)

        # Set user as online
        await self.set_user_online(user_id)

        self.logger.info(
            f"User {user_id} connected (connection_id: {connection_id})"
        )

        # Send connection success message
        await self.send_personal_message(
            connection_id,
            {
                "type": "connection_established",
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return connection_id

    async def disconnect(self, connection_id: str, user_id: str):
        """
        Remove Websocket connection and update user status.

        :param connection_id: Connection ID to disconnect
        :param user_id: User ID from JWT token
        """
        # Remove from local connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if connection_id in self.heartbeat:
            del self.heartbeat[connection_id]

        # Remove from Redis
        await self._remove_user_connection(user_id, connection_id)

        # Check if user has other active connections
        connections = await self._get_user_connections(user_id)
        if not connections:
            # No more active connections - set user offline
            await self.set_user_offline(user_id)

        self.logger.info(
            f"User {user_id} disconnected (connection_id: {connection_id})"
        )

    # ================ Heartbeat management ================

    async def update_heartbeat(self, connection_id: str) -> bool:
        """
        Update heartbeat timestamp

        :param connection_id: Connection ID

        :return: True if connection is valid
        """
        if connection_id in self.active_connections:
            self.heartbeat[connection_id] = datetime.now(timezone.utc)
            return True
        return False

    async def check_stale_connections(self, timeout_seconds: int = 60):
        """
        Check for connections that haven't sent heartbeat and close them.

        :param timeout_seconds: Seconds without heartbeat before disconnect
        """
        now = datetime.now(timezone.utc)
        stale_connections = []

        for connection_id, last_heartbeat in self.heartbeat.items():
            elapsed = (now - last_heartbeat).total_seconds()
            if elapsed > timeout_seconds:
                stale_connections.append(connection_id)

        for connection_id in stale_connections:
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.close(code=1000, reason="Heartbeat timeout")
                except Exception as e:
                    self.logger.error(
                        f"Error closing stale connection {connection_id}: {e}"
                    )

                # Clean up
                del self.active_connections[connection_id]
                del self.heartbeat[connection_id]

                self.logger.warning(
                    f"Closed stale connection: {connection_id} "
                    f"(no heartbeat for {elapsed:.0f}s)"
                )

    # ================ Messaging ================

    async def send_personal_message(
        self, connection_id: str, message: dict[str, Any]
    ):
        """
        Send message to specific connection.

        :param connection_id: Target connection ID
        :param message: Message dict to send
        """
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_json(message)
            except Exception as e:
                self.logger.error(
                    f"Error sending message to {connection_id}: {e}"
                )

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        """
        Send message to all connections of a user (across all servers).

        :param user_id: Target user ID
        :param message: Message dict to send
        """
        channel = f"user:{user_id}"
        await self.redis.publish(channel, message)

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: dict[str, Any],
        exclude_user_id: str | None = None,
    ):
        """
        Broadcast message to all users in a conversation.

        :param conversation_id: Target conversation ID
        :param message: Message dict to send
        :param exclude_user_id: Optional user ID to exclude from broadcast
        """
        channel = f"conversation:{conversation_id}"
        payload = {"message": message, "exclude_user_id": exclude_user_id}
        await self.redis.publish(channel, payload)

    # ================ User presence ================

    async def set_user_online(self, user_id: str):
        """Mark user as online in Redis"""
        await self.redis.hset(f"user:presence:{user_id}", "status", "online")
        await self.redis.hset(
            f"user:presence:{user_id}",
            "last_seen",
            datetime.now(timezone.utc).isoformat(),
        )
        await self.redis.expire(f"user:presence:{user_id}", 3600)  # 1 hour TTL

        # Broadcast presence update
        await self.redis.publish(
            "presence",
            {
                "type": "user_online",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def set_user_offline(self, user_id: str):
        """Mark user as offline in Redis"""
        await self.redis.hset(f"user:presence:{user_id}", "status", "offline")
        await self.redis.hset(
            f"user:presence:{user_id}",
            "last_seen",
            datetime.now(timezone.utc).isoformat(),
        )

        # Broadcast presence update
        await self.redis.publish(
            "presence",
            {
                "type": "user_offline",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def get_user_presence(self, user_id: str) -> dict[str, Any]:
        """Get user presence status from Redis"""
        presence = await self.redis.hgetall(f"user:presence:{user_id}")
        if not presence:
            return {"status": "offline", "last_seen": None}
        return presence

    async def set_typing_status(
        self, conversation_id: str, user_id: str, is_typing: bool
    ):
        """
        Update typing status for user in conversation.

        :param conversation_id: Conversation ID
        :param user_id: User ID
        :param is_typing: True if user is typing
        """
        key = f"conversation:typing:{conversation_id}"
        now = datetime.now(timezone.utc).isoformat()

        if is_typing:
            # Set typing status with 5 second TTL
            await self.redis.hset(key, user_id, now)
            await self.redis.expire(key, 5)
        else:
            # Remove typing status
            await self.redis.hdel(key, user_id)

        # Broadcast typing status
        await self.broadcast_to_conversation(
            conversation_id,
            {
                "type": "typing",
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": now,
            },
            exclude_user_id=user_id,
        )

    # ================ Redis helper methods ================

    async def _add_user_connection(self, user_id: str, connection_id: str):
        """Add connection to user's connection set in Redis"""
        await self.redis.sadd(f"user:connections:{user_id}", connection_id)
        await self.redis.expire(f"user:connections:{user_id}", 3600)

    async def _remove_user_connection(self, user_id: str, connection_id: str):
        """Remove connection from user's connection set in Redis"""
        await self.redis.srem(f"user:connections:{user_id}", connection_id)

    async def _get_user_connections(self, user_id: str) -> set:
        """Get all connection IDs for a user from Redis"""
        return await self.redis.smembers(f"user:connections:{user_id}")

    # ================ Pub/Sub listener ================

    async def start_pubsub_listener(self):
        """
        Start Redis pub/sub listener for cross-server communication.
        This should be called once on application startup.
        """
        try:
            # Subscribe to relevant channels
            # We'll subscribe to pattern channels for users and conversations
            await self.redis.subscribe("presence")

            self.logger.info("Started Redis pub/sub listener")

            # Start listening loop
            self.pubsub_task = asyncio.create_task(self._pubsub_listener_loop())

        except Exception as e:
            self.logger.error(f"Failed to start pub/sub listener: {e}")
            raise

    async def _pubsub_listener_loop(self):
        """Main loop for processing pub/sub messages"""
        while True:
            try:
                message = await self.redis.get_message(
                    ignore_subscribe_messages=True
                )

                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    # Handle presence updates
                    if channel == "presence":
                        await self._handle_presence_message(data)

                    # Handle user-specific messages
                    elif channel.startswith("user:"):
                        user_id = channel.split(":", 1)[1]
                        await self._handle_user_message(user_id, data)

                    # Handle conversation messages
                    elif channel.startswith("conversation:"):
                        await self._handle_conversation_message(data)

                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Error in pub/sub listener loop: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _handle_presence_message(self, data: dict[str, Any]):
        """Handle presence update messages"""
        # Broadcast to all local connections
        for connection_id in self.active_connections:
            await self.send_personal_message(connection_id, data)

    async def _handle_user_message(self, user_id: str, message: dict[str, Any]):
        """Handle messages targeted at specific user"""
        # Find local connections for this user
        connections = await self._get_user_connections(user_id)
        for connection_id in connections:
            if connection_id in self.active_connections:
                await self.send_personal_message(connection_id, message)

    async def _handle_conversation_message(self, data: dict):
        """Handle messages for conversation"""
        message = data.get("message", {})
        _ = data.get("exclude_user_id")

        # Broadcast to all local connections except excluded user
        for connection_id, websocket in self.active_connections.items():
            # TODO: Check if connection belongs to conversation participant
            # For now, we'll need to track user_id with connection_id
            await self.send_personal_message(connection_id, message)

    async def stop_pubsub_listener(self):
        """Stop pub/sub listener (called on shutdown)"""
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
        await self.redis.unsubscribe("presence")
        self.logger.info("Stopped Redis pub/sub listener")


connection_manager = ConnectionManager()
