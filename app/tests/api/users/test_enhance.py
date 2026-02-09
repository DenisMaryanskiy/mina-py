import pytest
from httpx import AsyncClient

from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_enhance_user_profile_success(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/users/enhance",
        json={
            "avatar_url": "https://example.com/avatar.jpg",
            "status": "Feeling great!",
        },
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == "https://example.com/avatar.jpg"
    assert data["status"] == "Feeling great!"
    assert data["email"] == login_user.user.email


@pytest.mark.asyncio
async def test_enhance_user_profile_partial_data(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/users/enhance",
        json={"avatar_url": None, "status": "Feeling great!"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] is None
    assert data["status"] == "Feeling great!"
    assert data["email"] == login_user.user.email


@pytest.mark.asyncio
async def test_enhance_user_invalid_url(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/users/enhance",
        json={"avatar_url": "invalid_url", "status": "Feeling great!"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Validation error"
    assert data["errors"][0]["message"] == (
        "Value error, Avatar URL must start with http:// or https://"
    )
