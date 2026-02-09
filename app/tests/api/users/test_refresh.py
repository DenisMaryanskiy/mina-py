import pytest
from httpx import AsyncClient

from app.core.security import create_refresh_token
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_refresh_token_success(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/users/refresh",
        headers={"Authorization": f"Bearer {login_user.token.refresh_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid_token(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/refresh",
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_refresh_token_non_existent_user(async_client: AsyncClient):
    # Create a refresh token for a non-existent user ID
    fake_user_id = "123e4567-e89b-12d3-a456-426614174000"
    refresh_token = create_refresh_token(fake_user_id)

    response = await async_client.post(
        "/api/v1/users/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "User account is not active or deleted"
