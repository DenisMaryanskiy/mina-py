import faker
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User
from app.schemas.users import LoginResponse

f = faker.Faker()


@pytest.fixture
def test_user_id() -> str:
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def test_token(test_user_id: str) -> str:
    return create_access_token(test_user_id)


# === Seed entities for API and utils tests ===
@pytest_asyncio.fixture
async def seed_activated_user(async_session: AsyncSession):
    """Seed activated user into Postgres test DB."""
    u = User(
        id=f.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=True,
        activation_token="token",
    )
    async_session.add(u)
    await async_session.commit()
    yield u


@pytest_asyncio.fixture
async def seed_activated_users(async_session: AsyncSession):
    """Seed activated user into Postgres test DB."""
    u1, u2, u3 = [
        User(
            id=f.uuid4(),
            username=f.user_name(),
            email=f.email(),
            password_hash=hash_password("S!trongP@ssw0rd!"),
            is_active=True,
            activation_token="token",
        )
        for _ in range(3)
    ]
    async_session.add_all([u1, u2, u3])
    await async_session.commit()
    yield [u1, u2, u3]


@pytest_asyncio.fixture
async def login_user(async_client: AsyncClient, seed_activated_user: User):
    """Log in seeded user and return access token."""
    response = await async_client.post(
        "/api/v1/users/login",
        json={
            "username_or_email": seed_activated_user.email,
            "password": "S!trongP@ssw0rd!",
        },
    )
    data = response.json()
    yield LoginResponse(**data)


@pytest_asyncio.fixture
async def seed_direct_conversation(
    async_session: AsyncSession,
    seed_activated_user: User,
    seed_activated_users: list[User],
) -> Conversation:
    u1 = seed_activated_users[0]
    conv = Conversation(type="direct", created_by=seed_activated_user.id)
    async_session.add(conv)
    await async_session.flush()

    for user, role in [(seed_activated_user, "admin"), (u1, "member")]:
        p = ConversationParticipant(
            conversation_id=conv.id, user_id=user.id, role=role
        )
        async_session.add(p)

    await async_session.commit()
    await async_session.refresh(conv)
    return conv


@pytest_asyncio.fixture
async def seed_group_conversation(
    async_session: AsyncSession,
    seed_activated_user: User,
    seed_activated_users: list[User],
) -> Conversation:
    u1, u2, u3 = seed_activated_users
    conv = Conversation(
        type="group", name="Test Group", created_by=seed_activated_user.id
    )
    async_session.add(conv)
    await async_session.flush()

    for user, role in [
        (seed_activated_user, "admin"),
        (u1, "member"),
        (u2, "member"),
        (u3, "member"),
    ]:
        p = ConversationParticipant(
            conversation_id=conv.id, user_id=user.id, role=role
        )
        async_session.add(p)

    await async_session.commit()
    await async_session.refresh(conv)
    return conv


@pytest_asyncio.fixture
async def seed_message(
    async_session: AsyncSession,
    seed_direct_conversation: Conversation,
    seed_activated_user: User,
) -> Message:
    msg = Message(
        conversation_id=seed_direct_conversation.id,
        sender_id=seed_activated_user.id,
        content="Hello, world!",
        message_type="text",
    )
    async_session.add(msg)
    await async_session.commit()
    await async_session.refresh(msg)
    return msg
