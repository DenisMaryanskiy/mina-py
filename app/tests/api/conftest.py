import secrets

import faker
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.users import User

f = faker.Faker()


# === Seed entities for API and utils tests ===
@pytest_asyncio.fixture
async def seed_user(async_session: AsyncSession):
    """Seed user into Postgres test DB."""
    u = User(
        id=f.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password(
            f.password(
                length=12, special_chars=True, digits=True, upper_case=True
            )
        ),
        activation_token=secrets.token_urlsafe(32),
    )
    async_session.add(u)
    await async_session.commit()
    yield u


@pytest_asyncio.fixture
async def seed_activated_user(async_session: AsyncSession):
    """Seed activated user into Postgres test DB."""
    u = User(
        id=f.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password(
            f.password(
                length=12, special_chars=True, digits=True, upper_case=True
            )
        ),
        is_active=True,
        activation_token="token",
    )
    async_session.add(u)
    await async_session.commit()
    yield u
