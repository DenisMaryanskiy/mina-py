import logging

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app

logger = logging.getLogger(__name__)

settings = get_settings()
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.TEST_POSTGRES_USER}:{settings.TEST_POSTGRES_PASSWORD}@{settings.TEST_POSTGRES_HOST}:{settings.TEST_POSTGRES_PORT}/{settings.TEST_POSTGRES_DB}"

# === Test DB setup ===
engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture()
async def test_session_engine():
    """Фикстура для мока движка на всю сессию тестов"""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


# === Apply migrations once ===
@pytest.fixture(scope="session", autouse=True)
def migrate_db():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


# === DB session per test ===
@pytest_asyncio.fixture()
async def async_session(test_session_engine: AsyncEngine):
    async with test_session_engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await conn.close()


# === Dependency override ===
@pytest_asyncio.fixture(autouse=True)
async def override_get_db(async_session):
    async def _get_db():
        yield async_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


# === Async test client ===
@pytest_asyncio.fixture()
async def async_client():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client
