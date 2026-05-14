import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_get_user_profile_success(
    async_client: AsyncClient,
    login_user: LoginResponse,
    seed_activated_user: User,
):
    response = await async_client.get(
        f"/api/v1/users/{seed_activated_user.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(seed_activated_user.id)
    assert data["username"] == seed_activated_user.username
    assert "email" not in data
    assert "is_active" not in data
    assert "is_deleted" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_user_profile_not_found(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_get_user_profile_soft_deleted(
    async_client: AsyncClient,
    login_user: LoginResponse,
    async_session: AsyncSession,
):
    deleted_user = User(
        username="deleted_profile_user",
        email="deleted_profile@example.com",
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=True,
        is_deleted=True,
        activation_token="tok",
    )
    async_session.add(deleted_user)
    await async_session.commit()

    response = await async_client.get(
        f"/api/v1/users/{deleted_user.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_profile_unauthenticated(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.get(f"/api/v1/users/{seed_activated_user.id}")
    assert response.status_code == 401
