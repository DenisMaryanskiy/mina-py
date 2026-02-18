import json
from logging import Logger
from typing import Any, Set

import redis.asyncio as redis
from redis.asyncio.client import PubSub

from app.core.config import Settings, get_settings
from app.core.logger import get_logger


class RedisClient:
    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ):
        self.redis: redis.Redis | None = None
        self.pubsub: PubSub | None = None

        self.settings = settings or get_settings()
        self.logger = logger or get_logger()

    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=self.settings.REDIS_DECODE_RESPONSES,
                max_connections=self.settings.REDIS_POOL_SIZE,
            )

            await self.redis.ping()
            self.logger.info("Redis connection established successfully.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.logger.info("Redis connection closed.")

    # ============ Cache operations ==============

    async def get(self, key: str) -> str | None:
        """Get value from Redis by key."""
        try:
            if self.redis:
                return await self.redis.get(key)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set value in Redis with optional TTL (seconds)."""
        try:
            if self.redis:
                if ttl:
                    return await self.redis.setex(key, ttl, value)
                return await self.redis.set(key, value)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> int:
        """Delete key from Redis."""
        try:
            if self.redis:
                return await self.redis.delete(key) > 0
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis DELETE error for key {key}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            if self.redis:
                return await self.redis.exists(key) > 0
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for a key."""
        try:
            if self.redis:
                return await self.redis.expire(key, ttl)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    # ============ Hash operations ==============

    async def hget(self, name: str, key: str) -> str | None:
        """Get value from Redis hash."""
        try:
            if self.redis:
                return await self.redis.hget(name, key)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis HGET error for {name}:{key}: {e}")
            return None

    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in Redis hash."""
        try:
            if self.redis:
                return await self.redis.hset(name, key, value) > 0
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis HSET error for {name}:{key}: {e}")
            return False

    async def hgetall(self, name: str) -> dict:
        """Get all key-value pairs from Redis hash."""
        try:
            if self.redis:
                return await self.redis.hgetall(name)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis HGETALL error for {name}: {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete key from Redis hash."""
        try:
            if self.redis:
                return await self.redis.hdel(name, *keys) > 0
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis HDEL error for {name}: {e}")
            return 0

    # ============ Set operations ==============

    async def sadd(self, key: str, *values: str) -> int:
        """Add values to Redis set."""
        try:
            if self.redis:
                return await self.redis.sadd(key, *values)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis SADD error for {key}: {e}")
            return 0

    async def srem(self, key: str, *values: str) -> int:
        """Remove values from Redis set."""
        try:
            if self.redis:
                return await self.redis.srem(key, *values)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis SREM error for {key}: {e}")
            return 0

    async def smembers(self, key: str) -> Set:
        """Get all members of Redis set."""
        try:
            if self.redis:
                return await self.redis.smembers(key)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis SMEMBERS error for {key}: {e}")
            return set()

    async def sismember(self, key: str, value: str) -> bool:
        """Check if value is a member of Redis set."""
        try:
            if self.redis:
                return await self.redis.sismember(key, value)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis SISMEMBER error for {key}: {e}")
            return False

    # ============ Pub/Sub operations ==============

    async def publish(self, channel: str, message: dict | str) -> int:
        """Publish message to Redis channel."""
        try:
            if self.redis:
                if isinstance(message, dict):
                    message = json.dumps(message)
                return await self.redis.publish(channel, message)
            else:
                raise
        except Exception as e:
            self.logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return 0

    async def subscribe(self, *channels: str):
        """Subscribe to Redis channels."""
        try:
            if self.redis:
                if not self.pubsub:
                    self.pubsub = self.redis.pubsub()
                await self.pubsub.subscribe(*channels)
                self.logger.info(f"Subscribed to Redis channels: {channels}")
            else:
                raise
        except Exception as e:
            self.logger.error(
                f"Redis SUBSCRIBE error for channels {channels}: {e}"
            )
            raise

    async def unsubscribe(self, *channels: str):
        """Unsubscribe from Redis channels."""
        try:
            if self.pubsub:
                await self.pubsub.unsubscribe(*channels)
                self.logger.info(f"Unsubscribed from Redis channels: {channels}")
        except Exception as e:
            self.logger.error(
                f"Redis UNSUBSCRIBE error for channels {channels}: {e}"
            )

    async def get_message(
        self, ignore_subscribe_messages: bool = True
    ) -> dict | None:
        """Get message from subscribed channels."""
        try:
            if not self.pubsub:
                return None
            return await self.pubsub.get_message(
                ignore_subscribe_messages=ignore_subscribe_messages
            )
        except Exception as e:
            self.logger.error(f"Redis GET_MESSAGE error: {e}")
            return None

    # ============ JSON operations ==============

    async def get_json(self, key: str) -> Any:
        """Get JSON value from Redis."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode JSON for key {key}")
        return None

    async def set_json(
        self, key: str, value: Any, ttl: int | None = None
    ) -> bool:
        """Set JSON value in Redis."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False


redis_client = RedisClient()


def get_redis() -> RedisClient:
    """Dependency to get Redis client instance."""
    return redis_client
