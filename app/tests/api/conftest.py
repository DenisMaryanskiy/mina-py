import faker
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.users import User
from app.schemas.users import LoginResponse

f = faker.Faker()


@pytest.fixture
def test_user_id() -> str:
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def test_token(test_user_id: str) -> str:
    return create_access_token(test_user_id)


# === Seed entities for API and utils tests ===
@pytest_asyncio.fixture
async def seed_activated_user(async_session: AsyncSession):
    """Seed activated user into Postgres test DB."""
    u = User(
        id=f.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=True,
        activation_token="token",
    )
    async_session.add(u)
    await async_session.commit()
    yield u


@pytest_asyncio.fixture
async def login_user(async_client: AsyncClient, seed_activated_user: User):
    """Log in seeded user and return access token."""
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.email,
            "password": "S!trongP@ssw0rd!",
        },
    )
    data = response.json()
    yield LoginResponse(**data)
