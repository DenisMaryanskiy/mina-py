import json
from logging import Logger
from typing import Callable

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue

from app.core.config import Settings, get_settings
from app.core.logger import get_logger


class RabbitMQClient:
    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ):
        self.settings = settings or get_settings()
        self.logger = logger or get_logger()

        self.connection: AbstractConnection | None = None
        self.channel: AbstractChannel | None = None
        self.queues: dict[str, AbstractQueue] = {}

    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            connection_url = (
                f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASS}"
                f"@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}"
                f"{self.settings.RABBITMQ_VHOST}"
            )
            self.connection = await aio_pika.connect_robust(connection_url)
            self.channel = await self.connection.channel()

            # Set QoS to process one message at a time
            await self.channel.set_qos(prefetch_count=1)

            self.logger.info("RabbitMQ connection established successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Close RabbitMQ connection."""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        self.logger.info("RabbitMQ connection closed")

    async def declare_queue(
        self, queue_name: str, durable: bool = True, declare_dlq: bool = True
    ) -> AbstractQueue:
        """
        Declare a queue with optional durability and dead-letter queue (DLQ).

        :param queue_name: Name of the queue to declare
        :param durable: Whether the queue should survive broker restarts
        :param declare_dlq: Whether to declare a corresponding dead-letter queue

        :return: The declared queue object
        """

        if not self.channel:
            raise RuntimeError("RabbitMQ channel is not initialized")

        # Declare DLQ if requested
        dlx_name = None
        if declare_dlq:
            dlx_name = f"{queue_name}.dlx"
            dlq_name = f"{queue_name}.dlq"

            # Declare the dead-letter exchange
            dlx = await self.channel.declare_exchange(
                dlx_name, ExchangeType.DIRECT, durable=True
            )

            # Declare the dead-letter queue and bind it to the DLX
            dlq = await self.channel.declare_queue(dlq_name, durable=True)

            # Bind the DLQ to the DLX with the same routing key as the main queue
            await dlq.bind(dlx, routing_key=queue_name)
            self.logger.info(f"Dead letter queue declared: {dlq_name}")

        # Declare the main queue with DLX settings if DLQ is declared
        queue_args = {}
        if dlx_name:
            queue_args = {
                "x-dead-letter-exchange": dlx_name,
                "x-dead-letter-routing-key": queue_name,
            }

        queue = await self.channel.declare_queue(
            queue_name, durable=durable, arguments=queue_args
        )

        self.queues[queue_name] = queue
        self.logger.info(f"Queue declared: {queue_name}")
        return queue

    async def publish(
        self,
        queue_name: str,
        message: dict | str,
        priority: int = 0,
        persistent: bool = True,
    ) -> bool:
        """
        Publish a message to the specified queue.

        :param queue_name: Name of the target queue
        :param message: The message to publish
        (dict will be converted to JSON string)
        :param priority: Message priority (0-9, higher = more priority)
        :param persistent: Whether the message should be persisted to disk

        :return: True if the message was published successfully, False otherwise
        """

        try:
            if not self.channel:
                raise RuntimeError("RabbitMQ channel is not initialized")

            # Ensure the target queue exists before publishing
            if queue_name not in self.queues:
                await self.declare_queue(queue_name)

            if isinstance(message, dict):
                message = json.dumps(message)

            delivery_mode = (
                DeliveryMode.PERSISTENT
                if persistent
                else DeliveryMode.NOT_PERSISTENT
            )

            msg = Message(
                body=message.encode(),
                delivery_mode=delivery_mode,
                priority=priority,
                content_type="application/json",
            )

            await self.channel.default_exchange.publish(
                msg, routing_key=queue_name
            )
            self.logger.debug(f"Message published to queue '{queue_name}'")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to publish message to queue '{queue_name}': {e}"
            )
            return False

    async def consume(
        self, queue_name: str, callback: Callable, auto_ack: bool = False
    ):
        """
        Start consuming messages from the specified queue.

        :param queue_name: Name of the queue to consume from
        :param callback: Async function to process each message
        :param auto_ack: Whether to automatically acknowledge messages
        """

        try:
            if queue_name not in self.queues:
                await self.declare_queue(queue_name)

            queue = self.queues[queue_name]

            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process(ignore_processed=auto_ack):
                    try:
                        body = json.loads(message.body.decode())
                        await callback(body)

                        if not auto_ack:
                            await message.ack()
                    except json.JSONDecodeError:
                        self.logger.error(
                            f"Invalid JSON in message: {message.body}"
                        )
                        if not auto_ack:
                            await message.reject(requeue=False)
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                        if not auto_ack:
                            await message.reject(requeue=False)

            await queue.consume(message_handler)
            self.logger.info(f"Started consuming from queue '{queue_name}'")
        except Exception as e:
            self.logger.error(
                f"Failed to start consuming from queue '{queue_name}': {e}"
            )
            raise

    async def get_queue_size(self, queue_name: str) -> int:
        """Get the number of messages in the specified queue."""
        try:
            if queue_name not in self.queues:
                return 0
            queue = self.queues[queue_name]
            return queue.declaration_result.message_count
        except Exception as e:
            self.logger.error(f"Failed to get size of queue '{queue_name}': {e}")
            return 0

    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from the specified queue."""
        try:
            if queue_name not in self.queues:
                return 0
            queue = self.queues[queue_name]
            result = await queue.purge()
            self.logger.info(f"Queue '{queue_name}' purged successfully")
            return result
        except Exception as e:
            self.logger.error(f"Failed to purge queue '{queue_name}': {e}")
            return 0


rabbitmq_client = RabbitMQClient()


async def get_rabbitmq_client() -> RabbitMQClient:
    """Dependency to get the RabbitMQ client instance."""
    return rabbitmq_client


# ==================== Queue Names ====================
# Define queue names as constants for consistency

QUEUE_MESSAGE_DELIVERY = "message_delivery"
QUEUE_NOTIFICATIONS = "notifications"
QUEUE_MEDIA_PROCESSING = "media_processing"
QUEUE_EMAIL = "email"

# List of all queues to initialize
ALL_QUEUES = [
    QUEUE_MESSAGE_DELIVERY,
    QUEUE_NOTIFICATIONS,
    QUEUE_MEDIA_PROCESSING,
    QUEUE_EMAIL,
]
