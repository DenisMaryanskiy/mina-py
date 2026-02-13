from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient

from app.core.storage import MinioStorage
from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_avatar_upload_success(
    async_client: AsyncClient,
    login_user: LoginResponse,
    storage: MinioStorage,
    sample_image: BytesIO,
):
    with patch("app.api.users.avatar.minio_storage", storage):
        files = {"file": ("avatar.jpg", sample_image, "image/jpeg")}

        response = await async_client.post(
            "/api/v1/users/avatar/upload",
            files=files,
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data


@pytest.mark.asyncio
async def test_delete_avatar_success(
    async_client: AsyncClient,
    login_user: LoginResponse,
    storage: MinioStorage,
    sample_image: BytesIO,
):
    with patch("app.api.users.avatar.minio_storage", storage):
        files = {"file": ("avatar.jpg", sample_image, "image/jpeg")}
        upload_response = await async_client.post(
            "/api/v1/users/avatar/upload",
            files=files,
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )
        assert upload_response.status_code == 200

        response = await async_client.post(
            "/api/v1/users/avatar/delete",
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["avatar_url"] is None


@pytest.mark.asyncio
async def test_delete_avatar_storage_exception_raises_500(
    async_client: AsyncClient, login_user: LoginResponse, sample_image: BytesIO
):
    """
    Test that delete_avatar raises 500 when MinIO delete raises an exception.
    This tests the case where delete_avatar itself throws an error.
    """
    mock_storage = Mock(spec=MinioStorage)

    mock_storage.upload_avatar = AsyncMock(
        return_value="http://localhost:9000/avatars/user/avatar.jpg"
    )

    mock_storage.delete_avatar = Mock(return_value=False)

    with patch("app.api.users.avatar.minio_storage", mock_storage):
        files = {"file": ("avatar.jpg", sample_image, "image/jpeg")}
        upload_response = await async_client.post(
            "/api/v1/users/avatar/upload",
            files=files,
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )
        assert upload_response.status_code == 200

        delete_response = await async_client.post(
            "/api/v1/users/avatar/delete",
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )

        assert delete_response.status_code == 500
