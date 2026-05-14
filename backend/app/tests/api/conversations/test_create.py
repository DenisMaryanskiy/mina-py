import uuid

import pytest
from httpx import AsyncClient

from app.models.conversations import Conversation
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_create_direct_conversation(
    async_client: AsyncClient,
    seed_activated_users: list[User],
    login_user: LoginResponse,
):
    another_user = seed_activated_users[0]
    response = await async_client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [str(another_user.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "direct"
    assert len(data["participants"]) == 2


@pytest.mark.asyncio
async def test_create_direct_conversation_deduplicates(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
    seed_activated_users: list[User],
):
    u1 = seed_activated_users[0]
    response = await async_client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [str(u1.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(seed_direct_conversation.id)


@pytest.mark.asyncio
async def test_create_direct_conversation_many_participants(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
    seed_activated_users: list[User],
):
    u1, u2 = seed_activated_users[:2]
    response = await async_client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [str(u1.id), str(u2.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_group_without_name_fails(
    async_client: AsyncClient, seed_activated_users: list[User], login_user
):
    second_activated_user = seed_activated_users[0]
    response = await async_client.post(
        "/api/v1/conversations",
        json={
            "type": "group",
            "participant_ids": [str(second_activated_user.id)],
        },
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_direct_with_nonexistent_user_fails(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_direct_with_yourself(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [str(login_user.user.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400
