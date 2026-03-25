import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User


@pytest_asyncio.fixture
async def seed_group_message(
    async_session: AsyncSession,
    seed_group_conversation: Conversation,
    seed_activated_user: User,
) -> Message:
    """A message inside the group conversation sent by the admin user."""
    msg = Message(
        conversation_id=seed_group_conversation.id,
        sender_id=seed_activated_user.id,
        content="Hello group!",
        message_type="text",
    )
    async_session.add(msg)
    await async_session.commit()
    await async_session.refresh(msg)
    return msg
