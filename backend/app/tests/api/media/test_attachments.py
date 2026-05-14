import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.attachments import MessageAttachment
from app.models.messages import Message
from app.models.users import User


@pytest.mark.asyncio
async def test_list_attachments(
    async_client: AsyncClient,
    seeded_attachment: tuple[MessageAttachment, Message, User],
):
    att, msg, user = seeded_attachment
    token = create_access_token(str(user.id))

    resp = await async_client.get(
        f"/api/v1/media/attachments/{msg.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["id"] == str(att.id)
    assert data[0]["file_type"] == "image"


@pytest.mark.asyncio
async def test_list_attachments_nonexistent_message(
    async_client: AsyncClient, media_user: User
):
    token = create_access_token(str(media_user.id))
    resp = await async_client.get(
        f"/api/v1/media/attachments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_attachment(
    async_client: AsyncClient,
    seeded_attachment: tuple[MessageAttachment, Message, User],
):
    att, _, user = seeded_attachment
    token = create_access_token(str(user.id))

    with patch(
        "app.api.media.attachments.media_storage.delete_attachment",
        return_value=True,
    ):
        resp = await async_client.delete(
            f"/api/v1/media/attachments/{att.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_attachment_returns_404(
    async_client: AsyncClient, media_user: User
):
    token = create_access_token(str(media_user.id))
    resp = await async_client.delete(
        f"/api/v1/media/attachments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_another_user_returns_403(
    async_client: AsyncClient,
    seed_activated_user: User,
    seeded_attachment: tuple[MessageAttachment, Message, User],
):
    att, _, _ = seeded_attachment
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.delete(
        f"/api/v1/media/attachments/{att.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_attachment_orphaned_message_returns_500(
    async_client: AsyncClient,
    async_session: AsyncSession,
    seeded_attachment: tuple[MessageAttachment, Message, User],
):
    att, _, user = seeded_attachment
    token = create_access_token(str(user.id))

    real_execute = async_session.execute

    call_count = 0

    async def patched_execute(stmt, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            empty = MagicMock(spec=Result)
            empty.scalars.return_value.first.return_value = None
            return empty
        return await real_execute(stmt, *args, **kwargs)

    with patch.object(async_session, "execute", side_effect=patched_execute):
        resp = await async_client.delete(
            f"/media/attachments/{att.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 500
    assert "Data integrity issue" in resp.json()["detail"]
