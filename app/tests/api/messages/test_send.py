import uuid

import pytest
from httpx import AsyncClient

from app.models.conversations import Conversation
from app.models.messages import Message
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_send_message(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        json={"content": "Hello!", "message_type": "text"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello!"
    assert data["message_type"] == "text"
    assert data["is_edited"] is False
    assert data["is_deleted"] is False


@pytest.mark.asyncio
async def test_send_text_message_no_content(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        json={"message_type": "text"},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


async def test_send_message_with_reply(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_message: Message,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        json={
            "content": "Reply here!",
            "message_type": "text",
            "reply_to_message_id": str(seed_message.id),
        },
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["reply_to_message_id"] == str(seed_message.id)


async def test_send_message_with_non_existent_reply(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        json={
            "content": "Reply here!",
            "message_type": "text",
            "reply_to_message_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404
