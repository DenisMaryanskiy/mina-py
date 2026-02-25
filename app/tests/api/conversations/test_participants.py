import uuid

import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.conversations import Conversation
from app.models.users import User
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_admin_can_add_participants(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    login_user: LoginResponse,
    async_session: AsyncSession,
):
    fk = Faker()
    new_user = User(
        username=fk.user_name(),
        email=fk.email(),
        password_hash=hash_password("S!trongP@ssw0rd!"),
        is_active=True,
        activation_token="tok",
    )
    async_session.add(new_user)
    await async_session.commit()

    response = await async_client.post(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants",
        json={"user_ids": [str(new_user.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(new_user.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_add_participants(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    second_activated_user, third_activated_user, _ = seed_activated_users
    token = create_access_token(str(second_activated_user.id))
    response = await async_client.post(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants",
        json={"user_ids": [str(third_activated_user.id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_add_participants_conversation_not_found(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        f"/api/v1/conversations/{str(uuid.uuid4())}/participants",
        json={"user_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_participants_to_direct_conversation(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/conversations/{seed_direct_conversation.id}/participants",
        json={"user_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_participants_user_not_exists(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants",
        json={"user_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_participants_existing_participant(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants",
        json={"user_ids": [str(login_user.user.id)]},
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_admin_can_remove_participant(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
    login_user: LoginResponse,
):
    second_activated_user = seed_activated_users[0]
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants/{second_activated_user.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_remove_participant_from_direct(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    seed_activated_users: list[User],
    login_user: LoginResponse,
):
    second_activated_user = seed_activated_users[0]
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_direct_conversation.id}/participants/{second_activated_user.id}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_non_admin_cannot_remove_participants(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    seed_activated_users: list[User],
):
    second_activated_user, third_activated_user, _ = seed_activated_users
    token = create_access_token(str(second_activated_user.id))
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants/{str(third_activated_user.id)}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_non_existent_participant(
    async_client: AsyncClient,
    seed_group_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.delete(
        f"/api/v1/conversations/{seed_group_conversation.id}/participants/{str(uuid.uuid4())}",
        headers={"Authorization": f"Bearer {login_user.token.access_token}"},
    )
    assert response.status_code == 404
