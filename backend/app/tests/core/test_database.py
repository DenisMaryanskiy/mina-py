import pytest
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_production_uses_prod_credentials(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("POSTGRES_USER", "prod_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "prod_pass")
    monkeypatch.setenv("POSTGRES_HOST", "prod-host")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "prod_db")

    # Reload settings to pick up new environment
    import importlib

    from app.core import config

    importlib.reload(config)

    settings = config.get_settings()

    expected_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    assert settings.ENVIRONMENT == "prod"
    assert "prod_user" in expected_url
    assert "prod_pass" in expected_url
    assert "prod_db" in expected_url

    from app.core import database

    importlib.reload(database)

    # Mask password for comparison
    expected_url = expected_url.replace("prod_pass", "***")
    async for session in database.get_db():
        assert session.bind.url.render_as_string() == expected_url
        break  # Only test first yield


@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    from app.core.database import get_db

    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break  # Only test first yield
