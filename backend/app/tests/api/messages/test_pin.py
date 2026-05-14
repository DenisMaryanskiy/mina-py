import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.pinned_messages import PinnedMessage
from app.models.users import User

# ── helpers ──────────────────────────────────────────────────────────────────


async def _make_group_message(
    session: AsyncSession, conv: Conversation, sender: User
) -> Message:
    msg = Message(
        conversation_id=conv.id,
        sender_id=sender.id,
        content="Pin me!",
        message_type="text",
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


# ── POST /messages/{id}/pin ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pin_message_success(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/messages/{msg.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["message_id"] == str(msg.id)
    assert data["conversation_id"] == str(seed_group_conversation.id)
    assert data["pinned_by"] == str(seed_activated_user.id)


@pytest.mark.asyncio
async def test_pin_message_duplicate_returns_409(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    token = create_access_token(str(seed_activated_user.id))
    headers = {"Authorization": f"Bearer {token}"}
    url = f"/api/v1/messages/{msg.id}/pin"

    await async_client.post(url, headers=headers)
    resp = await async_client.post(url, headers=headers)
    assert resp.status_code == 409
    assert "already pinned" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_pin_message_by_member_returns_403(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    # seed_activated_users[0] is a member, not admin
    member = seed_activated_users[0]
    token = create_access_token(str(member.id))
    resp = await async_client.post(
        f"/api/v1/messages/{msg.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pin_message_not_found_returns_404(
    async_client: AsyncClient, seed_activated_user: User
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/messages/{uuid.uuid4()}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pin_message_in_direct_conv_returns_400(
    async_client: AsyncClient, seed_message: Message, seed_activated_user: User
):
    # seed_message is in a direct conversation
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/messages/{seed_message.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "group" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pin_message_unauthenticated_returns_401(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    resp = await async_client.post(f"/api/v1/messages/{msg.id}/pin")
    assert resp.status_code == 401


# ── DELETE /messages/{id}/pin ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unpin_message_success(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    token = create_access_token(str(seed_activated_user.id))
    headers = {"Authorization": f"Bearer {token}"}
    url = f"/api/v1/messages/{msg.id}"

    # Pin first
    pin_resp = await async_client.post(f"{url}/pin", headers=headers)
    assert pin_resp.status_code == 201

    # Unpin
    resp = await async_client.delete(f"{url}/pin", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unpin_message_not_pinned_returns_404(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.delete(
        f"/api/v1/messages/{msg.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert "not pinned" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unpin_message_by_member_returns_403(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
    seed_activated_users: list[User],
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    # Pin as admin
    pin = PinnedMessage(
        conversation_id=seed_group_conversation.id,
        message_id=msg.id,
        pinned_by=seed_activated_user.id,
    )
    async_session.add(pin)
    await async_session.commit()

    # Try to unpin as member
    member = seed_activated_users[0]
    token = create_access_token(str(member.id))
    resp = await async_client.delete(
        f"/api/v1/messages/{msg.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unpin_message_not_found_returns_404(
    async_client: AsyncClient, seed_activated_user: User
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.delete(
        f"/api/v1/messages/{uuid.uuid4()}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unpin_message_in_direct_conv_returns_400(
    async_client: AsyncClient, seed_message: Message, seed_activated_user: User
):
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.delete(
        f"/api/v1/messages/{seed_message.id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "group" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unpin_message_unauthenticated_returns_401(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
):
    msg = await _make_group_message(
        async_session, seed_group_conversation, seed_activated_user
    )
    resp = await async_client.delete(f"/api/v1/messages/{msg.id}/pin")
    assert resp.status_code == 401
