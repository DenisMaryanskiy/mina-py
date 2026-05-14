import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.messages import Message
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_delete_own_message(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.delete(
        f"/api/v1/messages/{seed_message.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


async def test_delete_others_message_fails(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    second_activated_user = seed_activated_users[1]
    token = create_access_token(str(second_activated_user.id))
    response = await async_client.delete(
        f"/api/v1/messages/{seed_message.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
