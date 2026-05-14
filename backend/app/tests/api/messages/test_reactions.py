import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User
from app.schemas.users import LoginResponse

# ── Helpers ──────────────────────────────────────────────────────────────────


def _reactions_url(message_id) -> str:
    return f"/api/v1/messages/{message_id}/reactions"


def _reaction_url(message_id, emoji: str) -> str:
    return f"/api/v1/messages/{message_id}/reactions/{emoji}"


def _auth(login: LoginResponse) -> dict:
    return {"Authorization": f"Bearer {login.token.access_token}"}


# ── POST /messages/{message_id}/reactions ────────────────────────────────────


@pytest.mark.asyncio
async def test_add_reaction_success(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["emoji"] == "👍"
    assert data["message_id"] == str(seed_message.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_add_reaction_duplicate_returns_409(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    response = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_different_emojis_same_message_allowed(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    r1 = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    r2 = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "❤️"},
        headers=_auth(login_user),
    )
    assert r1.status_code == 201
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_add_reaction_missing_emoji_field(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.post(
        _reactions_url(seed_message.id), json={}, headers=_auth(login_user)
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_reaction_empty_emoji_string(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": ""},
        headers=_auth(login_user),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_reaction_unauthenticated(
    async_client: AsyncClient, seed_message: Message
):
    response = await async_client.post(
        _reactions_url(seed_message.id), json={"emoji": "👍"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_reaction_nonexistent_message(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.post(
        _reactions_url(uuid.uuid4()),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_reaction_not_participant(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    # seed_activated_users[2] is not added to the direct conversation
    outsider_token = create_access_token(str(seed_activated_users[2].id))
    response = await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


# ── DELETE /messages/{message_id}/reactions/{emoji} ──────────────────────────


@pytest.mark.asyncio
async def test_remove_reaction_success(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    response = await async_client.delete(
        _reaction_url(seed_message.id, "👍"), headers=_auth(login_user)
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_reaction_not_found(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.delete(
        _reaction_url(seed_message.id, "👍"), headers=_auth(login_user)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_reaction_nonexistent_message(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.delete(
        _reaction_url(uuid.uuid4(), "👍"), headers=_auth(login_user)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_others_reaction_not_found(
    async_client: AsyncClient,
    seed_message: Message,
    login_user: LoginResponse,
    seed_activated_users: list[User],
):
    # user1 (login_user) adds a reaction
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    # seed_activated_users[0] is the other participant in the direct conversation
    other_token = create_access_token(str(seed_activated_users[0].id))
    response = await async_client.delete(
        _reaction_url(seed_message.id, "👍"),
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_reaction_not_participant(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    outsider_token = create_access_token(str(seed_activated_users[2].id))
    response = await async_client.delete(
        _reaction_url(seed_message.id, "👍"),
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remove_reaction_unauthenticated(
    async_client: AsyncClient, seed_message: Message
):
    response = await async_client.delete(_reaction_url(seed_message.id, "👍"))
    assert response.status_code == 401


# ── GET /messages/{message_id}/reactions ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_reactions_empty(
    async_client: AsyncClient, seed_message: Message, login_user: LoginResponse
):
    response = await async_client.get(
        _reactions_url(seed_message.id), headers=_auth(login_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message_id"] == str(seed_message.id)
    assert data["reactions"] == []


@pytest.mark.asyncio
async def test_get_reactions_grouped_by_emoji(
    async_client: AsyncClient,
    seed_message: Message,
    login_user: LoginResponse,
    seed_activated_users: list[User],
):
    # login_user adds 👍
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers=_auth(login_user),
    )
    # seed_activated_users[0] is also a participant — adds 👍
    other_token = create_access_token(str(seed_activated_users[0].id))
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "👍"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    # login_user also adds ❤️
    await async_client.post(
        _reactions_url(seed_message.id),
        json={"emoji": "❤️"},
        headers=_auth(login_user),
    )

    response = await async_client.get(
        _reactions_url(seed_message.id), headers=_auth(login_user)
    )
    assert response.status_code == 200
    data = response.json()
    reactions = {item["emoji"]: item for item in data["reactions"]}
    assert "👍" in reactions
    assert reactions["👍"]["count"] == 2
    assert len(reactions["👍"]["user_ids"]) == 2
    assert "❤️" in reactions
    assert reactions["❤️"]["count"] == 1


@pytest.mark.asyncio
async def test_get_reactions_nonexistent_message(
    async_client: AsyncClient, login_user: LoginResponse
):
    response = await async_client.get(
        _reactions_url(uuid.uuid4()), headers=_auth(login_user)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_reactions_not_participant(
    async_client: AsyncClient,
    seed_message: Message,
    seed_activated_users: list[User],
):
    outsider_token = create_access_token(str(seed_activated_users[2].id))
    response = await async_client.get(
        _reactions_url(seed_message.id),
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_reactions_unauthenticated(
    async_client: AsyncClient, seed_message: Message
):
    response = await async_client.get(_reactions_url(seed_message.id))
    assert response.status_code == 401


# ── MessageResponse integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_message_response_has_reactions_field(
    async_client: AsyncClient,
    seed_direct_conversation: Conversation,
    login_user: LoginResponse,
):
    response = await async_client.post(
        f"/api/v1/messages/{seed_direct_conversation.id}",
        json={"content": "Hello!", "message_type": "text"},
        headers=_auth(login_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert "reactions" in data
    assert data["reactions"] == []
