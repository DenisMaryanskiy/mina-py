import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.messages import Message
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_edit_own_message(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.patch(
        f"/api/v1/messages/{seed_message.id}",
        json={"content": "Edited content"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Edited content"
    assert data["is_edited"] is True


@pytest.mark.asyncio
async def test_edit_others_message_fails(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    second_activated_user = seed_activated_users[1]
    token = create_access_token(str(second_activated_user.id))
    response = await async_client.patch(
        f"/api/v1/messages/{seed_message.id}",
        json={"content": "Hacked!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_edit_nonexistent_message_fails(
    async_client: AsyncClient, login_user
):
    response = await async_client.patch(
        f"/api/v1/messages/{uuid.uuid4()}",
        json={"content": "Edited"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404
