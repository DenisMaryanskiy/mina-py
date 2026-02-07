import pytest
from httpx import AsyncClient

from app.models.users import User


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/register",
        json={
            "email": "mail@example.org",
            "username": "JohnDoe",
            "password": "StrongP@ssw0rd!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "mail@example.org"
    assert data["username"] == "JohnDoe"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_register_duplicate_email(
    async_client: AsyncClient, seed_user: User
):
    response = await async_client.post(
        "/api/v1/users/register",
        json={
            "email": seed_user.email,
            "username": "NewUser",
            "password": "AnotherP@ssw0rd!",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already registered."


@pytest.mark.asyncio
async def test_register_duplicate_username(
    async_client: AsyncClient, seed_user: User
):
    response = await async_client.post(
        "/api/v1/users/register",
        json={
            "email": "new_email@example.org",
            "username": seed_user.username,
            "password": "AnotherP@ssw0rd!",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username is already taken."
