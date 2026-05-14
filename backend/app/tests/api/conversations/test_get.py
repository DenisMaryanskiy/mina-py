import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_list_conversations_by_user(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = [c["id"] for c in response.json()]
    assert str(seed_direct_conversation.id) in ids


@pytest.mark.asyncio
async def test_get_conversation_by_id(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.get(
        f"/api/v1/conversations/{seed_direct_conversation.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(seed_direct_conversation.id)
    assert len(data["participants"]) == 2


@pytest.mark.asyncio
async def test_get_conversation_by_id_not_found(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.get(
        f"/api/v1/conversations/{str(uuid.uuid4())}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404


async def test_get_conversation_not_participant_returns_403(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_activated_users: list[User],
):
    third_activated_user = seed_activated_users[2]
    token = create_access_token(str(third_activated_user.id))
    response = await async_client.get(
        f"/api/v1/conversations/{seed_direct_conversation.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
