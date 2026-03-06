import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.security import create_access_token
from app.models.conversations import Conversation
from app.models.messages import Message
from app.models.users import User


def _make_jpg_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_single_image(
    async_client: AsyncClient,
    media_conversation_with_message: tuple[Conversation, Message, User],
):
    _, msg, user = media_conversation_with_message
    token = create_access_token(str(user.id))
    jpg = _make_jpg_bytes()

    with patch(
        "app.api.media.upload.media_storage.upload_attachment",
        new_callable=AsyncMock,
        return_value={
            "file_type": "image",
            "original_filename": "photo.jpg",
            "file_url": "http://minio/attachments/photo.jpg",
            "thumbnail_url": "http://minio/attachments/photo_thumb.jpg",
            "file_size": len(jpg),
            "mime_type": "image/jpeg",
            "dimensions": {"width": 100, "height": 100},
            "metadata_": {"resolutions": ["thumbnail", "medium", "full"]},
        },
    ):
        resp = await async_client.post(
            f"/api/v1/media/upload/{msg.id}",
            files=[("files", ("photo.jpg", jpg, "image/jpeg"))],
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["file_type"] == "image"
    assert data[0]["thumbnail_url"] is not None


@pytest.mark.asyncio
async def test_upload_to_nonexistent_message_returns_404(
    async_client: AsyncClient, media_user: User
):
    token = create_access_token(str(media_user.id))
    resp = await async_client.post(
        f"/api/v1/media/upload/{uuid.uuid4()}",
        files=[("files", ("x.jpg", _make_jpg_bytes(), "image/jpeg"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_another_user_returns_403(
    async_client: AsyncClient,
    seed_activated_user: User,
    media_conversation_with_message: tuple[Conversation, Message, User],
):
    _, msg, _ = media_conversation_with_message
    token = create_access_token(str(seed_activated_user.id))
    resp = await async_client.post(
        f"/api/v1/media/upload/{msg.id}",
        files=[("files", ("x.jpg", _make_jpg_bytes(), "image/jpeg"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == (
        "You can only attach files to your own messages."
    )
