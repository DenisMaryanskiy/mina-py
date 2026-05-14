import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.messages import Message
from app.models.users import User


@pytest.mark.asyncio
async def test_mark_message_read(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    """Second user (participant) marks the message as read."""
    second_activated_user = seed_activated_users[0]
    token = create_access_token(str(second_activated_user.id))
    response = await async_client.post(
        f"/api/v1/messages/{seed_message.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "read" in response.json()["message"]
