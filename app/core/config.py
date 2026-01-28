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
    TEST_POSTGRES_PORT: str = "5432"

    ENVIRONMENT: str = "dev"  # dev or prod

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
