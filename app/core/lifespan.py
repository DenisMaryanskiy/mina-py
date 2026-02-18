from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logger import get_logger
from app.core.rabbitmq import ALL_QUEUES, rabbitmq_client
from app.core.redis import redis_client
from app.core.websocket import connection_manager

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles initialization and cleanup of Redis, RabbitMQ, and WebSocket.
    """
    # Startup
    logger.info("Starting MINA application...")

    try:
        # Initialize Redis
        await redis_client.connect()
        logger.info("Redis initialized")

        # Initialize RabbitMQ
        await rabbitmq_client.connect()

        # Declare all queues
        for queue_name in ALL_QUEUES:
            await rabbitmq_client.declare_queue(queue_name)

        logger.info("RabbitMQ initialized")

        # Start Websocket Pub/Sub listener
        await connection_manager.start_pubsub_listener()
        logger.info("Websocket manager initialized")

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down MINA application...")

    try:
        # Stop WebSocket pub/sub listener
        await connection_manager.stop_pubsub_listener()

        # Close RabbitMQ
        await rabbitmq_client.disconnect()

        # Close Redis
        await redis_client.disconnect()

        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
