import uuid
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from minio import Minio, S3Error

from app.core.storage import MinioStorage


@pytest.mark.asyncio
async def test_delete_avatar_success(
    storage: MinioStorage,
    valid_jpeg_file: UploadFile,
    test_user_uuid: uuid.UUID,
    minio_client: Minio,
    cleanup_bucket,
):
    url = await storage.upload_avatar(valid_jpeg_file, test_user_uuid)
    object_name = url.split(f"/{storage.bucket_name}/")[-1]

    assert minio_client.stat_object(storage.bucket_name, object_name)

    result = storage.delete_avatar(url)
    assert result is True

    with pytest.raises(S3Error):
        minio_client.stat_object(storage.bucket_name, object_name)


def test_delete_avatar_S3Error_raises_exception(
    storage: MinioStorage, minio_client: Minio
):
    with patch.object(storage.client, "remove_object") as mock_remove:
        mock_remove.side_effect = S3Error(
            code="NoSuchKey",
            message="Key does not exist",
            resource="object_name",
            request_id="123",
            host_id="456",
            response="error",
        )

        result = storage.delete_avatar("url_with_nonexistent_object")

        assert result is False
