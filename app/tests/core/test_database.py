import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    from app.core.database import get_db

    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break  # Only test first yield
