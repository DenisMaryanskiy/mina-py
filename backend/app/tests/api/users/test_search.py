import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_search_users_by_username(
    async_client: AsyncClient,
    login_user: LoginResponse,
    seed_activated_user: User,
):
    response = await async_client.get(
        "/api/v1/users/search",
        params={"q": seed_activated_user.username[:4]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [u["id"] for u in data]
    assert str(seed_activated_user.id) in ids


@pytest.mark.asyncio
async def test_search_users_by_email(
    async_client: AsyncClient,
    login_user: LoginResponse,
    seed_activated_user: User,
):
    response = await async_client.get(
        "/api/v1/users/search",
        params={"q": seed_activated_user.email[:5]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert any(u["id"] == str(seed_activated_user.id) for u in data)


@pytest.mark.asyncio
async def test_search_users_empty_results(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.get(
        "/api/v1/users/search",
        params={"q": "zzz_no_match_xxxxxxxxxxx"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_excludes_inactive_users(
    async_client: AsyncClient,
    login_user: LoginResponse,
    async_session: AsyncSession,
):
    inactive = User(
        username="inactive_user_xyz",
        email="inactive_xyz@example.com",
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=False,
        activation_token="tok",
    )
    async_session.add(inactive)
    await async_session.commit()

    response = await async_client.get(
        "/api/v1/users/search",
        params={"q": "inactive_user_xyz"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_users_respects_limit(
    async_client: AsyncClient,
    login_user: LoginResponse,
    async_session: AsyncSession,
):
    for i in range(5):
        async_session.add(
            User(
                username=f"limituser_{i}",
                email=f"limituser_{i}@example.com",
                password_hash=hash_password("S!trongP@ssw0rd!"),
                is_active=True,
                activation_token="tok",
            )
        )
    await async_session.commit()

    response = await async_client.get(
        "/api/v1/users/search",
        params={"q": "limituser_", "limit": 3},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) <= 3


@pytest.mark.asyncio
async def test_search_users_missing_q(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.get(
        "/api/v1/users/search",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_users_unauthenticated(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/users/search", params={"q": "test"}
    )
    assert response.status_code == 401
