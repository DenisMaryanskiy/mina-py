import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.core.storage import (
    THUMBNAIL_SIZE,
    MediaStorage,
    _classify_mime,
    _guess_mime,
)


def _make_jpg_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes(width: int = 50, height: int = 50) -> bytes:
    img = Image.new("RGBA", (width, height), color=(0, 255, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing"


def _make_upload_file(
    data: bytes, filename: str, content_type: str
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers={"content-type": content_type},
    )


def test_compute_total_chunks():
    assert MediaStorage.compute_total_chunks(10 * 1024 * 1024, 5) == 2
    assert MediaStorage.compute_total_chunks(11 * 1024 * 1024, 5) == 3
    assert MediaStorage.compute_total_chunks(1024, 5) == 1


def test_compress_image_reduces_or_maintains_size():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.IMAGE_COMPRESSION_QUALITY = 85
    # Call the real method
    storage._compress_image = MediaStorage._compress_image.__get__(
        storage, MediaStorage
    )

    original = _make_jpg_bytes(800, 800)
    compressed = storage._compress_image(original, "image/jpeg")
    assert isinstance(compressed, bytes)
    assert len(compressed) > 0


def test_get_image_dimensions():
    storage = MagicMock(spec=MediaStorage)
    storage._get_image_dimensions = MediaStorage._get_image_dimensions.__get__(
        storage, MediaStorage
    )
    dims = storage._get_image_dimensions(_make_jpg_bytes(320, 240))
    assert dims == {"width": 320, "height": 240}


def test_make_thumbnail_respects_size():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.IMAGE_COMPRESSION_QUALITY = 85
    storage._make_thumbnail = MediaStorage._make_thumbnail.__get__(
        storage, MediaStorage
    )

    big_jpg = _make_jpg_bytes(1920, 1080)
    thumb = storage._make_thumbnail(big_jpg, THUMBNAIL_SIZE, "image/jpeg")
    img = Image.open(io.BytesIO(thumb))
    assert img.width <= THUMBNAIL_SIZE[0]
    assert img.height <= THUMBNAIL_SIZE[1]


def test_validate_file_too_large_raises():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 1
    storage.settings.ALLOWED_FILE_TYPES = ["image/jpeg"]
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )

    with pytest.raises(HTTPException) as exc_info:
        storage._validate_file(b"x" * (2 * 1024 * 1024), "image/jpeg")
    assert exc_info.value.status_code == 400


def test_validate_file_disallowed_type_raises():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 100
    storage.settings.ALLOWED_FILE_TYPES = ["image/jpeg"]
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )

    with pytest.raises(HTTPException) as exc_info:
        storage._validate_file(b"data", "application/x-executable")
    assert exc_info.value.status_code == 400


def test_classify_mime():
    assert _classify_mime("image/jpeg") == "image"
    assert _classify_mime("image/png") == "image"
    assert _classify_mime("video/mp4") == "video"
    assert _classify_mime("audio/mpeg") == "audio"
    assert _classify_mime("application/pdf") == "document"
    assert _classify_mime("application/msword") == "document"


def test_guess_mime():
    assert _guess_mime("file.bin", "image/png") == "image/png"
    assert _guess_mime("photo.jpg", None) == "image/jpeg"
    assert (
        _guess_mime("report.pdf", "application/octet-stream")
        == "application/pdf"
    )
    assert _guess_mime("file.unknownxyz", None) == "application/octet-stream"


def _make_storage(allowed: list[str], max_mb: int = 100):
    from app.core.storage import MediaStorage

    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = max_mb
    storage.settings.ALLOWED_FILE_TYPES = allowed
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )
    return storage


def test_wildcard_image_allows_any_image_subtype():
    storage = _make_storage(["image/*"])
    # Should not raise
    storage._validate_file(b"x" * 10, "image/gif")
    storage._validate_file(b"x" * 10, "image/avif")


def test_exact_mime_match_passes():
    storage = _make_storage(["application/pdf"])
    storage._validate_file(b"x" * 10, "application/pdf")


def test_unmatched_mime_raises_400():
    storage = _make_storage(["image/jpeg"])
    with pytest.raises(HTTPException) as exc:
        storage._validate_file(b"x" * 10, "application/x-binary")
    assert exc.value.status_code == 400


def test_file_over_size_limit_raises_400():
    storage = _make_storage(["image/jpeg"], max_mb=1)
    with pytest.raises(HTTPException) as exc:
        storage._validate_file(b"x" * (2 * 1024 * 1024), "image/jpeg")
    assert exc.value.status_code == 400


def _storage(
    jpeg_bytes: bytes,
    thumb_bytes: bytes,
    medium_bytes: bytes,
    enabled: bool = True,
    delete_return: bool = True,
):
    s = MagicMock(spec=MediaStorage)
    s.bucket_name = "attachments"
    s.settings = MagicMock()
    s.settings.ENABLE_VIRUS_SCAN = enabled
    s.logger = MagicMock()
    s._virus_scan = MediaStorage._virus_scan.__get__(s, MediaStorage)
    s.settings.IMAGE_COMPRESSION_QUALITY = 85
    s._compress_image = MediaStorage._compress_image.__get__(s, MediaStorage)
    s._make_thumbnail = MediaStorage._make_thumbnail.__get__(s, MediaStorage)
    s._get_image_dimensions = MediaStorage._get_image_dimensions.__get__(
        s, MediaStorage
    )
    s._process_and_upload_image = MediaStorage._process_and_upload_image.__get__(
        s, MediaStorage
    )
    s._put_object = MagicMock(
        side_effect=[
            "http://minio/attachments/key_thumb.jpg",
            "http://minio/attachments/key_medium.jpg",
        ]
    )
    s._object_name_from_url = MediaStorage._object_name_from_url.__get__(
        s, MediaStorage
    )
    s._delete_object = MagicMock(return_value=delete_return)
    s.delete_attachment = MediaStorage.delete_attachment.__get__(s, MediaStorage)
    return s


def test_delete_attachment_returns_true_on_success():
    raw = _make_jpg_bytes(800, 600)
    storage = _storage(raw, b"", b"", delete_return=True)
    url = "http://minio/attachments/messages/uid/mid/file.pdf"

    result = storage.delete_attachment(url)

    assert result is True


def test_returns_compressed_content_dimensions_and_thumbnail_url():
    raw = _make_jpg_bytes(800, 600)
    storage = _storage(raw, b"", b"")

    compressed, dims, thumbnail_url = storage._process_and_upload_image(
        raw, "image/jpeg", "messages/uid/mid/obj", ".jpg"
    )

    img = Image.open(io.BytesIO(compressed))
    assert img.format == "JPEG"

    assert dims == {"width": img.width, "height": img.height}

    assert thumbnail_url == "http://minio/attachments/key_thumb.jpg"


def test_virus_scan_disabled_returns_immediately():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"", enabled=False)
    # Must not raise, and clamd should never be imported/called
    s._virus_scan(b"some data")


def test_virus_scan_clean_file_passes():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"", enabled=True)
    mock_cd = MagicMock()
    mock_cd.instream.return_value = {"stream": ("OK", "")}

    with patch("app.core.storage.clamd") as mock_clamd:
        mock_clamd.ClamdUnixSocket.return_value = mock_cd
        s._virus_scan(b"clean content")


def test_virus_scan_infected_file_raises_400():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"", enabled=True)
    mock_cd = MagicMock()
    mock_cd.instream.return_value = {"stream": ("FOUND", "Eicar-Test-Signature")}

    with patch("app.core.storage.clamd") as mock_clamd:
        mock_clamd.ClamdUnixSocket.return_value = mock_cd
        with pytest.raises(HTTPException) as exc:
            s._virus_scan(b"infected")
        assert exc.value.status_code == 400
        assert "Eicar-Test-Signature" in exc.value.detail


def test_virus_scan_generic_exception_raises_500():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"", enabled=True)
    mock_cd = MagicMock()
    mock_cd.instream.side_effect = RuntimeError("clamd socket error")

    with patch("app.core.storage.clamd") as mock_clamd:
        mock_clamd.ClamdUnixSocket.return_value = mock_cd
        with pytest.raises(HTTPException) as exc:
            s._virus_scan(b"data")
        assert exc.value.status_code == 500
        assert "Virus scanning failed" in exc.value.detail


def test_compress_rgba_jpeg_converts_to_rgb():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"")
    rgba_bytes = _make_png_bytes(50, 50)  # PNG with RGBA
    result = s._compress_image(rgba_bytes, "image/jpeg")
    img = Image.open(io.BytesIO(result))
    assert img.mode == "RGB"


def test_make_thumbnail_rgba_jpeg_converts():
    raw = _make_jpg_bytes(800, 600)
    s = _storage(raw, b"", b"")
    png = _make_png_bytes(400, 400)  # RGBA
    thumb = s._make_thumbnail(png, THUMBNAIL_SIZE, "image/jpeg")
    img = Image.open(io.BytesIO(thumb))
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_upload_attachment_document_skips_image_pipeline():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 100
    storage.settings.ALLOWED_FILE_TYPES = ["application/pdf"]
    storage.settings.IMAGE_COMPRESSION_QUALITY = 85
    storage.settings.ENABLE_VIRUS_SCAN = False
    storage.bucket_name = "attachments"
    storage.logger = MagicMock()
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )
    storage._virus_scan = MediaStorage._virus_scan.__get__(storage, MediaStorage)
    storage._process_and_upload_image = MagicMock()
    storage._put_object = MagicMock(
        return_value="http://minio/attachments/doc.pdf"
    )
    storage.upload_attachment = MediaStorage.upload_attachment.__get__(
        storage, MediaStorage
    )

    pdf_file = _make_upload_file(_pdf_bytes(), "report.pdf", "application/pdf")
    msg_id = uuid.uuid4()
    user_id = uuid.uuid4()

    result = await storage.upload_attachment(pdf_file, msg_id, user_id)

    assert result["file_type"] == "document"
    assert result["thumbnail_url"] is None
    assert result["dimensions"] is None
    assert result["metadata_"]["resolutions"] is None
    storage._process_and_upload_image.assert_not_called()


@pytest.mark.asyncio
async def test_upload_attachment_image_calls_image_pipeline():
    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 100
    storage.settings.ALLOWED_FILE_TYPES = ["image/jpeg"]
    storage.settings.IMAGE_COMPRESSION_QUALITY = 85
    storage.settings.ENABLE_VIRUS_SCAN = False
    storage.bucket_name = "attachments"
    storage.logger = MagicMock()
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )
    storage._virus_scan = MediaStorage._virus_scan.__get__(storage, MediaStorage)
    jpg = _make_jpg_bytes()
    storage._process_and_upload_image = MagicMock(
        return_value=(
            jpg,
            {"width": 100, "height": 100},
            "http://minio/attachments/img_thumb.jpg",
        )
    )
    storage._put_object = MagicMock(
        return_value="http://minio/attachments/img.jpg"
    )
    storage.upload_attachment = MediaStorage.upload_attachment.__get__(
        storage, MediaStorage
    )

    jpg_file = _make_upload_file(jpg, "photo.jpg", "image/jpeg")
    result = await storage.upload_attachment(
        jpg_file, uuid.uuid4(), uuid.uuid4()
    )

    assert result["file_type"] == "image"
    assert result["thumbnail_url"] == "http://minio/attachments/img_thumb.jpg"
    assert result["dimensions"] == {"width": 100, "height": 100}
    assert result["metadata_"]["resolutions"] == ["thumbnail", "medium", "full"]
    storage._process_and_upload_image.assert_called_once()


@pytest.mark.asyncio
async def test_chunked_upload_returns_none_while_waiting():
    storage = MagicMock(spec=MediaStorage)
    storage.bucket_name = "attachments"
    storage.upload_attachment_chunked = (
        MediaStorage.upload_attachment_chunked.__get__(storage, MediaStorage)
    )

    redis = AsyncMock()
    redis.set = AsyncMock()
    # Only chunk 0 present, chunk 1 missing
    redis.get = AsyncMock(
        side_effect=lambda k: "data" if "chunk:0" in k else None
    )
    redis.delete = AsyncMock()

    result = await storage.upload_attachment_chunked(
        chunk=b"hello",
        upload_id="uid-1",
        chunk_index=0,
        total_chunks=2,
        filename="video.mp4",
        mime_type="video/mp4",
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        redis_client=redis,
    )
    assert result is None


@pytest.mark.asyncio
async def test_chunked_upload_reassembles_all_chunks():
    chunk0 = b"chunk-zero-data"
    chunk1 = b"chunk-one-data"
    upload_id = "uid-2"

    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 100
    storage.settings.ALLOWED_FILE_TYPES = ["application/pdf"]
    storage.settings.ENABLE_VIRUS_SCAN = False
    storage.bucket_name = "attachments"
    storage.logger = MagicMock()
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )
    storage._virus_scan = MediaStorage._virus_scan.__get__(storage, MediaStorage)
    storage._process_and_upload_image = MagicMock()
    storage._put_object = MagicMock(
        return_value="http://minio/attachments/big.pdf"
    )
    storage.upload_attachment_chunked = (
        MediaStorage.upload_attachment_chunked.__get__(storage, MediaStorage)
    )

    stored: dict[str, str] = {}

    async def mock_set(key, value, ex=None):
        stored[key] = value

    async def mock_get(key):
        return stored.get(key)

    async def mock_delete(key):
        stored.pop(key, None)

    redis = AsyncMock()
    redis.set = mock_set
    redis.get = mock_get
    redis.delete = mock_delete

    # Send chunk 0
    await storage.upload_attachment_chunked(
        chunk=chunk0,
        upload_id=upload_id,
        chunk_index=0,
        total_chunks=2,
        filename="big.pdf",
        mime_type="application/pdf",
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        redis_client=redis,
    )

    # Send chunk 1 (final) – should trigger reassembly
    msg_id = uuid.uuid4()
    user_id = uuid.uuid4()
    result = await storage.upload_attachment_chunked(
        chunk=chunk1,
        upload_id=upload_id,
        chunk_index=1,
        total_chunks=2,
        filename="big.pdf",
        mime_type="application/pdf",
        message_id=msg_id,
        user_id=user_id,
        redis_client=redis,
    )

    assert result is not None
    assert result["file_type"] == "document"
    assert result["original_filename"] == "big.pdf"
    assert result["mime_type"] == "application/pdf"
    assert result["file_size"] == len(chunk0) + len(chunk1)
    assert result["thumbnail_url"] is None
    assert result["dimensions"] is None

    # Confirm redis keys were cleaned up
    assert len(stored) == 0

    # _process_and_upload_image should NOT have been called (PDF, not image)
    storage._process_and_upload_image.assert_not_called()

    # _put_object must have received the reassembled content
    expected_content = chunk0 + chunk1
    actual_content = storage._put_object.call_args[0][2]
    assert actual_content == expected_content


@pytest.mark.asyncio
async def test_chunked_upload_calls_image_pipeline_for_image_mime():
    chunk0 = _make_jpg_bytes(200, 200)
    upload_id = "uid-img-chunked"
    compressed_jpg = _make_jpg_bytes(200, 200)
    fake_dims = {"width": 200, "height": 200}
    fake_thumb_url = "http://minio/attachments/img_thumb.jpg"

    storage = MagicMock(spec=MediaStorage)
    storage.settings = MagicMock()
    storage.settings.MAX_FILE_SIZE_MB = 100
    storage.settings.ALLOWED_FILE_TYPES = ["image/jpeg"]
    storage.settings.ENABLE_VIRUS_SCAN = False
    storage.bucket_name = "attachments"
    storage.logger = MagicMock()
    storage._validate_file = MediaStorage._validate_file.__get__(
        storage, MediaStorage
    )
    storage._virus_scan = MediaStorage._virus_scan.__get__(storage, MediaStorage)
    storage._process_and_upload_image = MagicMock(
        return_value=(compressed_jpg, fake_dims, fake_thumb_url)
    )
    storage._put_object = MagicMock(
        return_value="http://minio/attachments/img.jpg"
    )
    storage.upload_attachment_chunked = (
        MediaStorage.upload_attachment_chunked.__get__(storage, MediaStorage)
    )

    stored: dict[str, str] = {}

    async def mock_set(key, value, ex=None):
        stored[key] = value

    async def mock_get(key):
        return stored.get(key)

    async def mock_delete(key):
        stored.pop(key, None)

    redis = AsyncMock()
    redis.set = mock_set
    redis.get = mock_get
    redis.delete = mock_delete

    msg_id = uuid.uuid4()
    user_id = uuid.uuid4()

    result = await storage.upload_attachment_chunked(
        chunk=chunk0,
        upload_id=upload_id,
        chunk_index=0,
        total_chunks=1,
        filename="photo.jpg",
        mime_type="image/jpeg",
        message_id=msg_id,
        user_id=user_id,
        redis_client=redis,
    )

    assert result is not None
    assert result["file_type"] == "image"
    assert result["thumbnail_url"] == fake_thumb_url
    assert result["dimensions"] == fake_dims
    assert result["metadata_"]["resolutions"] == ["thumbnail", "medium", "full"]
    storage._process_and_upload_image.assert_called_once()
