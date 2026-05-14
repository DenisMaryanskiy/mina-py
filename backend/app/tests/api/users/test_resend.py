import pytest
from httpx import AsyncClient

from app.models.users import User


@pytest.mark.asyncio
async def test_resend_success(async_client: AsyncClient, seed_user: User):
    response = await async_client.post(
        "/api/v1/users/resend-activation",
        params={"username": seed_user.username},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == (
        "Activation email has been resent. Please check your inbox."
    )


@pytest.mark.asyncio
async def test_resend_user_not_found(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/users/resend-activation", params={"username": "nonexistentuser"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User with this username does not exist."


@pytest.mark.asyncio
async def test_resend_user_already_activated(
    async_client: AsyncClient, seed_activated_user: User
):
    response = await async_client.post(
        "/api/v1/users/resend-activation",
        params={"username": seed_activated_user.username},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Account is already activated."
