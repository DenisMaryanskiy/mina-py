import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.users import User


@pytest.mark.asyncio
async def test_update_group_name_success(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}",
        json={"name": "Renamed Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Renamed Group"
    assert data["id"] == str(seed_group_conversation.id)


@pytest.mark.asyncio
async def test_update_group_all_fields(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}",
        json={
            "name": "All Fields Group",
            "description": "A test description",
            "is_public": True,
            "max_participants": 500,
            "settings": {"theme": "dark"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "All Fields Group"
    assert data["description"] == "A test description"
    assert data["is_public"] is True
    assert data["max_participants"] == 500
    assert data["settings"] == {"theme": "dark"}


@pytest.mark.asyncio
async def test_update_group_partial_only_name(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}",
        json={"name": "Partial Update"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Partial Update"
    # Other fields stay at defaults
    assert data["is_public"] is False
    assert data["max_participants"] == 1000


@pytest.mark.asyncio
async def test_update_group_by_member_returns_403(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    # seed_activated_users[0] is a member (not admin) in seed_group_conversation
    member = seed_activated_users[0]
    token = create_access_token(str(member.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_group_not_found_returns_404(
    async_client: AsyncClient, seed_activated_user: User
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_direct_conversation_returns_404(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_direct_conversation.id}",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_group_unauthenticated_returns_401(
    async_client: AsyncClient, seed_group_conversation: Conversation
):
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}", json={"name": "No Auth"}
    )
    assert resp.status_code == 401
