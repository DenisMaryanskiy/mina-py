import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User


@pytest.mark.asyncio
async def test_init_chunked_upload(async_client: AsyncClient, media_user: User):
    token = create_access_token(str(media_user.id))
    file_size = 15 * 1024 * 1024

    resp = await async_client.post(
        "/api/v1/media/chunked/init",
        data={"file_size": file_size},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_chunks"] == 3
    assert "upload_id" in data
    assert data["chunk_size_bytes"] == 5 * 1024 * 1024


@pytest.mark.asyncio
async def test_send_chunk_incomplete(
    async_client: AsyncClient,
    media_conversation_with_message: tuple[Conversation, Message, User],
):
    _, msg, user = media_conversation_with_message
    token = create_access_token(str(user.id))
    chunk_data = b"x" * 1024

    with (
        patch(
            "app.api.media.chunked.media_storage.upload_attachment_chunked",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.media.chunked.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(
                get=AsyncMock(return_value="data"),
                set=AsyncMock(),
                delete=AsyncMock(),
            ),
        ),
    ):
        resp = await async_client.post(
            "/api/v1/media/chunked/chunk",
            data={
                "upload_id": str(uuid.uuid4()),
                "chunk_index": "0",
                "total_chunks": "3",
                "message_id": str(msg.id),
                "filename": "big_video.mp4",
                "mime_type": "video/mp4",
            },
            files=[
                ("chunk", ("chunk0", chunk_data, "application/octet-stream"))
            ],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["complete"] is False
    assert data["attachment"] is None


@pytest.mark.asyncio
async def test_send_final_chunk_creates_attachment(
    async_client: AsyncClient,
    media_conversation_with_message: tuple[Conversation, Message, User],
):
    _, msg, user = media_conversation_with_message
    token = create_access_token(str(user.id))
    upload_id = str(uuid.uuid4())

    completed_data = {
        "file_type": "document",
        "original_filename": "big.pdf",
        "file_url": "http://minio/attachments/big.pdf",
        "thumbnail_url": None,
        "file_size": 10 * 1024 * 1024,
        "mime_type": "application/pdf",
        "dimensions": None,
        "metadata_": {"upload_id": upload_id, "chunks": 2},
    }

    with (
        patch(
            "app.api.media.chunked.media_storage.upload_attachment_chunked",
            new_callable=AsyncMock,
            return_value=completed_data,
        ),
        patch(
            "app.api.media.chunked.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(
                get=AsyncMock(return_value=None),
                set=AsyncMock(),
                delete=AsyncMock(),
            ),
        ),
    ):
        resp = await async_client.post(
            "/media/chunked/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": "1",
                "total_chunks": "2",
                "message_id": str(msg.id),
                "filename": "big.pdf",
                "mime_type": "application/pdf",
            },
            files=[("chunk", ("c1", b"last chunk", "application/octet-stream"))],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["complete"] is True
    assert data["attachment"] is not None
    assert data["attachment"]["original_filename"] == "big.pdf"
    assert data["attachment"]["file_type"] == "document"
    assert data["chunks_received"] == data["total_chunks"] == 2


@pytest.mark.asyncio
async def test_send_chunk_message_not_found_returns_404(
    async_client: AsyncClient, media_user: User
):
    token = create_access_token(str(media_user.id))

    with patch(
        "app.api.media.chunked.get_redis",
        new_callable=AsyncMock,
        return_value=AsyncMock(get=AsyncMock(), set=AsyncMock()),
    ):
        resp = await async_client.post(
            "/media/chunked/chunk",
            data={
                "upload_id": str(uuid.uuid4()),
                "chunk_index": "0",
                "total_chunks": "2",
                "message_id": str(uuid.uuid4()),  # non-existent
                "filename": "file.mp4",
                "mime_type": "video/mp4",
            },
            files=[("chunk", ("c0", b"data", "application/octet-stream"))],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Message not found."


@pytest.mark.asyncio
async def test_send_chunk_by_non_owner_returns_403(
    async_client: AsyncClient,
    async_session: AsyncSession,
    media_conversation_with_message: tuple[Conversation, Message, User],
    seed_activated_user: User,
):
    _, msg, _ = media_conversation_with_message
    token = create_access_token(str(seed_activated_user.id))

    with patch(
        "app.api.media.chunked.get_redis",
        new_callable=AsyncMock,
        return_value=AsyncMock(get=AsyncMock(), set=AsyncMock()),
    ):
        resp = await async_client.post(
            "/media/chunked/chunk",
            data={
                "upload_id": str(uuid.uuid4()),
                "chunk_index": "0",
                "total_chunks": "1",
                "message_id": str(msg.id),
                "filename": "file.mp4",
                "mime_type": "video/mp4",
            },
            files=[("chunk", ("c0", b"data", "application/octet-stream"))],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403
