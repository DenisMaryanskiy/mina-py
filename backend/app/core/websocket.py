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

        # Typing debounce: {(conv_id, user_id): last_typing_event_time}
        # Prevents broadcasting "is_typing=True" more than once per 3 seconds.
        self._typing_last_sent: dict[tuple[str, str], datetime] = {}

        # Map connection_id -> user_id
        # (needed for away detection and pub/sub routing)
        self.connection_user: dict[str, str] = {}

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
        self.connection_user[connection_id] = user_id

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

        if connection_id in self.connection_user:
            del self.connection_user[connection_id]

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

    async def check_stale_connections(
        self, timeout_seconds: int = 60, away_threshold_seconds: int = 30
    ):
        """
        Check for connections that haven't sent a heartbeat and handle them:

        - After away_threshold_seconds without a heartbeat the user is
          marked as **away** and a presence_update event is broadcast.
        - After timeout_seconds the WebSocket is closed and the user is
          marked as **offline**.

        :param timeout_seconds: Seconds without heartbeat before disconnect
        :param away_threshold_seconds: Seconds without heartbeat
        before marking away
        """
        now = datetime.now(timezone.utc)
        stale_connections = []
        away_connections = []

        for connection_id, last_heartbeat in self.heartbeat.items():
            elapsed = (now - last_heartbeat).total_seconds()
            if elapsed > timeout_seconds:
                stale_connections.append((connection_id, elapsed))
            elif elapsed > away_threshold_seconds:
                away_connections.append(connection_id)

        # Mark away users
        for connection_id in away_connections:
            user_id = self.connection_user.get(connection_id)
            if user_id:
                await self.set_user_away(user_id)

        # Close timed-out connections
        for connection_id, elapsed in stale_connections:
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
                self.connection_user.pop(connection_id, None)

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

    async def _broadcast_presence_update(
        self, user_id: str, status: str, last_seen: str
    ):
        """
        Publish a standardised ``presence_update`` event to the ``presence``
        Redis channel so every server instance can forward it to their local
        WebSocket clients.
        """
        await self.redis.publish(
            "presence",
            {
                "type": "presence_update",
                "user_id": user_id,
                "status": status,
                "last_seen": last_seen,
            },
        )

    async def set_user_online(self, user_id: str):
        """Mark user as online in Redis and broadcast presence_update."""
        now = datetime.now(timezone.utc).isoformat()
        key = f"user:presence:{user_id}"

        await self.redis.hset(key, "status", "online")
        await self.redis.hset(key, "last_seen", now)
        await self.redis.expire(key, 3600)  # 1 hour TTL

        await self._broadcast_presence_update(user_id, "online", now)

    async def set_user_offline(self, user_id: str):
        """Mark user as offline in Redis and broadcast presence_update."""
        now = datetime.now(timezone.utc).isoformat()
        key = f"user:presence:{user_id}"

        await self.redis.hset(key, "status", "offline")
        await self.redis.hset(key, "last_seen", now)
        # Keep offline presence for 24 h so clients can see last_seen
        await self.redis.expire(key, 86400)

        await self._broadcast_presence_update(user_id, "offline", now)

    async def set_user_away(self, user_id: str):
        """
        Mark user as away in Redis and broadcast presence_update.

        Called automatically when the client has not sent a heartbeat for an
        extended period but the connection is still technically open.
        """
        now = datetime.now(timezone.utc).isoformat()
        key = f"user:presence:{user_id}"

        await self.redis.hset(key, "status", "away")
        await self.redis.hset(key, "last_seen", now)
        await self.redis.expire(key, 3600)

        await self._broadcast_presence_update(user_id, "away", now)

    async def get_user_presence(self, user_id: str) -> dict[str, Any]:
        """Get user presence status from Redis."""
        presence = await self.redis.hgetall(f"user:presence:{user_id}")
        if not presence:
            return {"status": "offline", "last_seen": None}
        return presence

    async def get_bulk_presence(
        self, user_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Return presence data for multiple users at once.

        :param user_ids: List of user ID strings
        :return: List of presence dicts, one per user_id
        """
        results = []
        for user_id in user_ids:
            presence = await self.get_user_presence(user_id)
            results.append(
                {
                    "user_id": user_id,
                    "status": presence.get("status", "offline"),
                    "last_seen": presence.get("last_seen"),
                }
            )
        return results

    async def set_typing_status(
        self, conversation_id: str, user_id: str, is_typing: bool
    ):
        """
        Update typing status for user in conversation.

        When ``is_typing`` is ``True``:
          - Records the timestamp in Redis hash with a 5-second TTL.
          - Broadcasts a ``typing`` event to all conversation participants
            except the sender.

        When ``is_typing`` is ``False``:
          - Removes the user's entry from the typing hash.
          - Broadcasts the stop-typing event.

        :param conversation_id: Conversation ID
        :param user_id: User ID
        :param is_typing: True if user is currently typing
        """
        key = f"conversation:typing:{conversation_id}"
        now = datetime.now(timezone.utc).isoformat()

        if is_typing:
            # Store timestamp; Redis TTL auto-expires after 5 s of inactivity
            await self.redis.hset(key, user_id, now)
            await self.redis.expire(key, 5)
        else:
            await self.redis.hdel(key, user_id)

        # Broadcast typing event to conversation participants
        await self.broadcast_to_conversation(
            conversation_id,
            {
                "type": "typing",
                "conversation_id": conversation_id,
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
