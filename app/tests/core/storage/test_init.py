import json

import pytest
from minio import Minio, S3Error

from app.core.storage import MinioStorage


def test_minio_storage_initialization(
    storage: MinioStorage, minio_client: Minio, test_bucket_name: str
):
    assert storage.bucket_name == test_bucket_name
    assert storage.client is not None

    assert minio_client.bucket_exists(test_bucket_name)


def test_bucket_exists_after_initialization(
    storage: MinioStorage, minio_client: Minio
):
    exists = minio_client.bucket_exists(storage.bucket_name)
    assert exists is True


def test_bucket_has_public_read_policy(
    storage: MinioStorage, minio_client: Minio
):
    policy_str = minio_client.get_bucket_policy(storage.bucket_name)
    policy = json.loads(policy_str)

    assert policy["Version"] == "2012-10-17"
    assert len(policy["Statement"]) == 1
    assert policy["Statement"][0]["Effect"] == "Allow"
    assert policy["Statement"][0]["Action"] == ["s3:GetObject"]


def test_ensure_bucket_exists_S3Error_raises_exception(
    storage: MinioStorage, minio_client: Minio, monkeypatch: pytest.MonkeyPatch
):
    def mock_bucket_exists(bucket_name):
        raise S3Error(
            code="InternalError",
            message="Server error",
            resource=bucket_name,
            request_id="123",
            host_id="456",
            response="error",
        )

    monkeypatch.setattr(storage.client, "bucket_exists", mock_bucket_exists)

    with pytest.raises(S3Error):
        storage._ensure_bucket_exists()
