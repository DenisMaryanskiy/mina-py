from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_DB: str = "db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    TEST_POSTGRES_DB: str = "test_db"
    TEST_POSTGRES_USER: str = "test_user"
    TEST_POSTGRES_PASSWORD: str = "test_password"
    TEST_POSTGRES_HOST: str = "localhost"
    TEST_POSTGRES_PORT: str = "5433"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: str = "587"
    SMTP_FROM: str = "test@example.org"
    SMTP_PASSWORD: str = "bebe baba bubu bibi"
    SMTP_STARTTLS: bool = True
    SMTPL_SSL_TLS: bool = False
    SMTP_USE_CREDENTIALS: bool = True
    SMTP_VALIDATE_CERTS: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_SECRET_KEY: str = "some-super-secret-key"
    JWT_ALGORITHM: str = "HS256"

    ENVIRONMENT: str = "dev"  # dev or prod

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
