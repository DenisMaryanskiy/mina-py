import pytest
from httpx import AsyncClient

from app.models.conversations import Conversation
from app.models.messages import Message
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_get_messages(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_message: Message,
    login_user: LoginResponse,
):
    response = await async_client.get(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_messages_with_search(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_message: Message,
    login_user: LoginResponse,
):
    # Use the first 5 characters of the message content
    search_term = seed_message.content[:5]
    response = await async_client.get(
        f"/api/v1/messages/{seed_direct_conversation.id}?search={search_term}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1
