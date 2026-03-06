import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.attachments import MessageAttachment
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User


@pytest_asyncio.fixture
async def media_user(async_session: AsyncSession):
    import faker

    f = faker.Faker()
    u = User(
        id=uuid.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=True,
        activation_token="tok",
    )
    async_session.add(u)
    await async_session.commit()
    yield u


@pytest_asyncio.fixture
async def media_conversation_with_message(
    async_session: AsyncSession, media_user: User, seed_activated_user: User
):
    conv = Conversation(id=uuid.uuid4(), type="direct", created_by=media_user.id)
    async_session.add(conv)
    await async_session.flush()

    part = ConversationParticipant(
        conversation_id=conv.id, user_id=media_user.id
    )
    async_session.add(part)
    await async_session.flush()

    part2 = ConversationParticipant(
        conversation_id=conv.id, user_id=seed_activated_user.id
    )
    async_session.add(part2)
    await async_session.flush()

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        sender_id=media_user.id,
        content="test",
        message_type="text",
    )
    async_session.add(msg)
    await async_session.commit()
    yield conv, msg, media_user


@pytest_asyncio.fixture
async def seeded_attachment(
    async_session: AsyncSession,
    media_conversation_with_message: tuple[Conversation, Message, User],
):
    _, msg, user = media_conversation_with_message
    att = MessageAttachment(
        id=uuid.uuid4(),
        message_id=msg.id,
        file_type="image",
        original_filename="test.jpg",
        file_url="http://minio/attachments/test.jpg",
        thumbnail_url="http://minio/attachments/test_thumb.jpg",
        file_size=12345,
        mime_type="image/jpeg",
        dimensions={"width": 100, "height": 100},
    )
    async_session.add(att)
    await async_session.commit()
    yield att, msg, user
