import uuid

import pytest
from httpx import AsyncClient

from app.models.conversations import Conversation
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_creator_deletes_conversation(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_direct_conversation.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Left conversation successfully."


@pytest.mark.asyncio
async def test_creator_deletes_group_conversation(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_group_conversation.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Conversation deleted successfully."


@pytest.mark.asyncio
async def test_delete_conversation_not_found(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.delete(
        f"/api/v1/conversations/{str(uuid.uuid4())}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404
