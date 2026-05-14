import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.users import User


@pytest.mark.asyncio
async def test_leave_group_as_member(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    # seed_activated_users[0] is a member
    member = seed_activated_users[0]
    token = create_access_token(str(member.id))
    resp = await async_client.post(
        f"/api/v1/groups/{seed_group_conversation.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "Left group successfully" in resp.json()["message"]


@pytest.mark.asyncio
async def test_leave_group_as_admin_with_other_admin(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    # Promote seed_activated_users[0] to admin, then original admin leaves
    result = await async_session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id
            == seed_group_conversation.id,
            ConversationParticipant.user_id == seed_activated_users[0].id,
        )
    )
    participant = result.scalars().first()
    participant.role = "admin"
    await async_session.commit()

    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/groups/{seed_group_conversation.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "Left group successfully" in resp.json()["message"]


@pytest.mark.asyncio
async def test_leave_group_as_last_admin_with_members_returns_400(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    # seed_activated_user is the only admin; other members exist → 400
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/groups/{seed_group_conversation.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "last admin" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_leave_group_as_last_person_deletes_conversation(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_activated_user: User,
):
    # Create a group with only the admin
    from app.models.conversation_participants import ConversationParticipant

    conv = Conversation(
        type="group", name="Solo Group", created_by=seed_activated_user.id
    )
    async_session.add(conv)
    await async_session.flush()
    p = ConversationParticipant(
        conversation_id=conv.id, user_id=seed_activated_user.id, role="admin"
    )
    async_session.add(p)
    await async_session.commit()

    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/groups/{conv.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"]

    # Verify conversation is gone
    result = await async_session.execute(
        select(Conversation).where(Conversation.id == conv.id)
    )
    assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_leave_direct_conversation_returns_404(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_activated_user: User,
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/groups/{seed_direct_conversation.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_leave_group_not_member_returns_403(
    async_client: AsyncClient, seed_group_conversation: Conversation
):
    # A random user who is not a participant
    token = create_access_token(str(uuid.uuid4()))
    resp = await async_client.post(
        f"/api/v1/groups/{seed_group_conversation.id}/leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Token is valid (JWT) but user doesn't exist → 403 from get_current_user
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_leave_group_unauthenticated_returns_401(
    async_client: AsyncClient, seed_group_conversation: Conversation
):
    resp = await async_client.post(
        f"/api/v1/groups/{seed_group_conversation.id}/leave"
    )
    assert resp.status_code == 401
