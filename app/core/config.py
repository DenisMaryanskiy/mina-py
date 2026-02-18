from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database settings
    POSTGRES_DB: str = "db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    # Test database settings
    TEST_POSTGRES_DB: str = "test_db"
    TEST_POSTGRES_USER: str = "test_user"
    TEST_POSTGRES_PASSWORD: str = "test_password"
    TEST_POSTGRES_HOST: str = "localhost"
    TEST_POSTGRES_PORT: str = "5433"

    # Email settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: str = "587"
    SMTP_FROM: str = "test@example.org"
    SMTP_PASSWORD: str = "bebe baba bubu bibi"
    SMTP_STARTTLS: bool = True
    SMTPL_SSL_TLS: bool = False
    SMTP_USE_CREDENTIALS: bool = True
    SMTP_VALIDATE_CERTS: bool = True

    # JWT settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_SECRET_KEY: str = "some-super-secret-key"
    JWT_ALGORITHM: str = "HS256"

    # MinIO settings
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio_access_key"
    MINIO_SECRET_KEY: str = "minio_secret_key"
    MINIO_BUCKET_NAME: str = "avatars"
    MINIO_SECURE: bool = False  # Set to True if using HTTPS
    MINIO_REGION: str = "eu-west-1"

    # Image upload settings
    MAX_IMAGE_SIZE_MB: str = "5"
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_POOL_SIZE: int = 10
    REDIS_DECODE_RESPONSES: bool = True

    # RabbitMQ settings
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_HEARTBEAT_TIMEOUT: int = 60  # seconds
    WS_MESSAGE_MAX_SIZE: int = 1024 * 1024  # 1MB

    # Other settings
    ENVIRONMENT: str = "dev"  # dev or prod

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
