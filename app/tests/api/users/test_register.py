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
async def test_register_invalid_username(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/register",
        json={
            "email": "mail@example.org",
            "username": "JD^",
            "password": "StrongP@ssw0rd!",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "username"]
    assert response.json()["detail"][0]["msg"] == (
        """Value error, Username can only contain letters,
                numbers, underscores, and hyphens."""
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password, error_msg",
    (
        pytest.param(
            "short",
            "Password must be at least 8 characters long.",
            id="too_short",
        ),
        pytest.param(
            "alllowercase1!",
            "Password must contain at least one uppercase letter.",
            id="missing_uppercase",
        ),
        pytest.param(
            "ALLUPPERCASE1!",
            "Password must contain at least one lowercase letter.",
            id="missing_lowercase",
        ),
        pytest.param(
            "NoDigits!",
            "Password must contain at least one digit.",
            id="missing_digit",
        ),
        pytest.param(
            "NoSpecialChar1",
            "Password must contain at least one special character.",
            id="missing_special_char",
        ),
    ),
)
async def test_register_invalid_password(
    async_client: AsyncClient, password: str, error_msg: str
):
    response = await async_client.post(
        "/api/v1/users/register",
        json={
            "email": "mail@example.org",
            "username": "JohnDoe",
            "password": password,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    if len(password) < 8:
        assert response.json()["detail"][0]["msg"] == (
            "String should have at least 8 characters"
        )
    else:
        assert response.json()["detail"][0]["msg"] == f"Value error, {error_msg}"


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
