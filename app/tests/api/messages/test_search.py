import pytest
from httpx import AsyncClient

from app.models.conversations import Conversation
from app.models.messages import Message
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_search_messages(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_message: Message,
    login_user: LoginResponse,
):
    response = await async_client.get(
        f"/api/v1/messages/{seed_direct_conversation.id}/search?q=Hello",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Hello"
    assert data["total"] >= 1
