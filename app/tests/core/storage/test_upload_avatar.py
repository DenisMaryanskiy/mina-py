import uuid

import pytest
from fastapi import HTTPException, UploadFile
from minio import Minio, S3Error

from app.core.storage import MinioStorage


@pytest.mark.asyncio
async def test_upload_avatar_success(
    storage: MinioStorage,
    valid_jpeg_file: UploadFile,
    test_user_uuid: uuid.UUID,
    minio_client: Minio,
    cleanup_bucket,
):
    url = await storage.upload_avatar(valid_jpeg_file, test_user_uuid)

    assert isinstance(url, str)
    assert storage.bucket_name in url
    assert str(test_user_uuid) in url
    assert url.endswith(".jpg")

    object_name = url.split(f"/{storage.bucket_name}/")[-1]
    stat = minio_client.stat_object(storage.bucket_name, object_name)
    assert stat is not None
    assert stat.size > 0


@pytest.mark.asyncio
async def test_upload_avatar_S3Error_raises_exception(
    storage: MinioStorage,
    valid_jpeg_file: UploadFile,
    test_user_uuid: uuid.UUID,
    minio_client: Minio,
    monkeypatch: pytest.MonkeyPatch,
):
    def mock_put_object(bucket_name, object_name, data, length, content_type):
        raise S3Error(
            code="InternalError",
            message="Server error",
            resource=bucket_name,
            request_id="123",
            host_id="456",
            response="error",
        )

    monkeypatch.setattr(storage.client, "put_object", mock_put_object)

    with pytest.raises(HTTPException) as exc_info:
        await storage.upload_avatar(valid_jpeg_file, test_user_uuid)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == (
            "Failed to upload image. Please try again later."
        )

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, S3Error)
