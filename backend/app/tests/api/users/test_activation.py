import pytest
from httpx import AsyncClient

from app.models.users import User


@pytest.mark.asyncio
async def test_activate_user_success(async_client: AsyncClient, seed_user: User):
    response = await async_client.get(
        f"/api/v1/users/activate/{seed_user.activation_token}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Account activated successfully."


@pytest.mark.asyncio
async def test_activate_user_invalid_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/users/activate/invalidtoken")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid activation token."


@pytest.mark.asyncio
async def test_activate_user_already_active(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.get(
        f"/api/v1/users/activate/{seed_activated_user.activation_token}"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Account is already activated."
