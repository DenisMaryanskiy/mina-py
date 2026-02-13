import pytest
from fastapi import HTTPException, UploadFile, status

from app.core.storage import MinioStorage


def test_validate_image_success_jpeg(
    storage: MinioStorage, valid_jpeg_file: UploadFile
):
    content = storage._validate_image(valid_jpeg_file)

    assert isinstance(content, bytes)
    assert len(content) > 0

    assert valid_jpeg_file.file.tell() == 0


def test_validate_image_invalid_extension(
    storage: MinioStorage, invalid_extension_file: UploadFile
):
    with pytest.raises(HTTPException) as exc_info:
        storage._validate_image(invalid_extension_file)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "Invalid" in exc_info.value.detail
        or "format" in exc_info.value.detail.lower()
    )


def test_validate_image_exceeds_size_limit(
    storage: MinioStorage, large_image_file: UploadFile
):
    with pytest.raises(HTTPException) as exc_info:
        storage._validate_image(large_image_file)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "exceed" in exc_info.value.detail.lower()
        or "limit" in exc_info.value.detail.lower()
    )


def test_validate_image_corrupted_file(
    storage: MinioStorage, corrupted_image_file: UploadFile
):
    with pytest.raises(HTTPException) as exc_info:
        storage._validate_image(corrupted_image_file)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "valid" in exc_info.value.detail.lower()
        or "image" in exc_info.value.detail.lower()
    )
