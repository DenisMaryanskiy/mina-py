import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


@pytest.mark.asyncio
async def test_login_success(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.email,
            "password": "S!trongP@ssw0rd!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    token = data["token"]
    assert "access_token" in token
    assert token["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_by_username(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.username,
            "password": "S!trongP@ssw0rd!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    token = data["token"]
    assert "access_token" in token
    assert token["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.email,
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email, username or password"


@pytest.mark.asyncio
async def test_login_invalid_username(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": "some_nonexistent_user",
            "password": "S!trongP@ssw0rd!",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email, username or password"


@pytest.mark.asyncio
async def test_login_inactive_user(async_client: AsyncClient, seed_user: User):
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_user.email,
            "password": "S!trongP@ssw0rd!",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "User account is not active or deleted"


@pytest.mark.asyncio
async def test_login_deleted_user(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_activated_user: User,
):
    seed_activated_user.is_deleted = True
    await async_session.commit()
    await async_session.refresh(seed_activated_user)

    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.email,
            "password": "S!trongP@ssw0rd!",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "User account is not active or deleted"
