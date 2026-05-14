import pytest
from httpx import AsyncClient

from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_update_status_success(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/users/status/update",
        json={"status": "Feeling great!"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Feeling great!"
    assert data["email"] == login_user.user.email
