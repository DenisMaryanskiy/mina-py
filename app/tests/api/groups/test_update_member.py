import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.users import User


@pytest.mark.asyncio
async def test_update_member_to_admin(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    # seed_activated_users[0] is a member; promote to admin
    member = seed_activated_users[0]
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{member.id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert data["user_id"] == str(member.id)


@pytest.mark.asyncio
async def test_update_member_to_member(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    # First promote seed_activated_users[0] to admin, then demote back
    member = seed_activated_users[0]
    from sqlalchemy import select

    result = await async_session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id
            == seed_group_conversation.id,
            ConversationParticipant.user_id == member.id,
        )
    )
    participant = result.scalars().first()
    participant.role = "admin"
    await async_session.commit()

    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{member.id}",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_update_member_by_non_admin_returns_403(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    # seed_activated_users[0] is member, tries to promote seed_activated_users[1]
    requester = seed_activated_users[0]
    target = seed_activated_users[1]
    token = create_access_token(str(requester.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{target.id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_member_not_in_group_returns_404(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{uuid.uuid4()}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_member_group_not_found_returns_404(
    async_client: AsyncClient,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{uuid.uuid4()}/members/{seed_activated_users[0].id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_member_invalid_role_returns_400(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{seed_activated_users[0].id}",
        json={"role": "superuser"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_member_unauthenticated_returns_401(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    resp = await async_client.patch(
        f"/api/v1/groups/{seed_group_conversation.id}/members/{seed_activated_users[0].id}",
        json={"role": "admin"},
    )
    assert resp.status_code == 401
