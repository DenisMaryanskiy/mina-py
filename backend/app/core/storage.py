import base64
import io
import json
import math
import mimetypes
import uuid
from logging import Logger
from pathlib import Path

import clamd
from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.logger import get_logger

# Module-level constants (used by MediaStorage)

_MIME_TO_FILE_TYPE: dict[str, str] = {
    "image": "image",
    "video": "video",
    "audio": "audio",
    "application": "document",
    "text": "document",
}

THUMBNAIL_SIZE: tuple[int, int] = (320, 320)
MEDIUM_SIZE: tuple[int, int] = (800, 800)

_PIL_FORMAT: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/gif": "GIF",
}

# Module-level helpers


def _classify_mime(mime_type: str) -> str:
    return _MIME_TO_FILE_TYPE.get(mime_type.split("/")[0], "document")


def _guess_mime(filename: str, content_type: str | None) -> str:
    if content_type and content_type != "application/octet-stream":
        return content_type
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


class BaseMinioStorage:
    """
    Shared MinIO client, bucket management, put/delete helpers,
    and URL generation.
    """

    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.logger = logger or get_logger()
        self.client = Minio(
            self.settings.MINIO_ENDPOINT,
            access_key=self.settings.MINIO_ACCESS_KEY,
            secret_key=self.settings.MINIO_SECRET_KEY,
            secure=self.settings.MINIO_SECURE,
        )

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Create bucket with public-read policy if it doesn't exist."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(
                    bucket_name, location=self.settings.MINIO_REGION
                )
                self.logger.info(f"Bucket '{bucket_name}' created successfully.")
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                        }
                    ],
                }
                self.client.set_bucket_policy(bucket_name, json.dumps(policy))
                self.logger.info(
                    f"Public read policy set for bucket '{bucket_name}'."
                )
        except S3Error as e:
            self.logger.error(f"Error creating bucket '{bucket_name}': {e}")
            raise

    def _get_public_url(self, bucket_name: str, object_name: str) -> str:
        protocol = "https" if self.settings.MINIO_SECURE else "http"
        return (
            f"{protocol}://{self.settings.MINIO_ENDPOINT}"
            f"/{bucket_name}/{object_name}"
        )

    def _put_object(
        self, bucket_name: str, object_name: str, data: bytes, mime_type: str
    ) -> str:
        """Upload bytes to MinIO and return the public URL."""
        try:
            self.client.put_object(
                bucket_name,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=mime_type,
            )
            self.logger.info(
                f"Uploaded '{object_name}' to bucket '{bucket_name}'."
            )
            return self._get_public_url(bucket_name, object_name)
        except S3Error as e:
            self.logger.error(f"Error uploading '{object_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage.",
            )

    def _delete_object(self, bucket_name: str, object_name: str) -> bool:
        try:
            self.client.remove_object(bucket_name, object_name)
            self.logger.info(
                f"Deleted '{object_name}' from bucket '{bucket_name}'."
            )
            return True
        except S3Error as e:
            self.logger.error(f"Error deleting '{object_name}': {e}")
            return False

    def _object_name_from_url(self, url: str, bucket_name: str) -> str:
        return url.split(f"/{bucket_name}/")[-1]


class AvatarStorage(BaseMinioStorage):
    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ) -> None:
        super().__init__(settings, logger)
        self.bucket_name = self.settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists(self.bucket_name)

    def _validate_image(self, file: UploadFile) -> bytes:
        """Extension whitelist, size cap, PIL integrity check."""
        ext = Path(file.filename).suffix.lower()
        if ext not in self.settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Allowed formats: "
                + ", ".join(self.settings.ALLOWED_EXTENSIONS),
            )

        content = file.file.read()
        file.file.seek(0)

        size_mb = len(content) / (1024 * 1024)
        if size_mb > float(self.settings.MAX_IMAGE_SIZE_MB):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image size exceeds the maximum limit of "
                f"{self.settings.MAX_IMAGE_SIZE_MB} MB.",
            )

        try:
            Image.open(io.BytesIO(content)).verify()
        except Exception as e:
            self.logger.error(f"Image validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid image.",
            )

        return content

    async def upload_avatar(self, file: UploadFile, user_id: uuid.UUID) -> str:
        """Validate and upload an avatar; return its public URL."""
        content = self._validate_image(file)
        ext = Path(file.filename).suffix.lower()
        object_name = f"{user_id}/{uuid.uuid4()}{ext}"
        mime = file.content_type or "application/octet-stream"
        return self._put_object(self.bucket_name, object_name, content, mime)

    def delete_avatar(self, avatar_url: str) -> bool:
        object_name = self._object_name_from_url(avatar_url, self.bucket_name)
        return self._delete_object(self.bucket_name, object_name)


class MediaStorage(BaseMinioStorage):
    """
    Message-attachment storage. Uses MEDIA_BUCKET_NAME.

    Adds: broad MIME allowlist, image compression + thumbnails,
    chunked upload via Redis, optional ClamAV virus scanning.
    """

    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ) -> None:
        super().__init__(settings, logger)
        self.bucket_name = self.settings.MEDIA_BUCKET_NAME
        self._ensure_bucket_exists(self.bucket_name)

    def _validate_file(self, content: bytes, mime_type: str) -> None:
        max_bytes = float(self.settings.MAX_FILE_SIZE_MB) * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of "
                f"{self.settings.MAX_FILE_SIZE_MB} MB.",
            )

        def _matches(mime: str) -> bool:
            for allowed in self.settings.ALLOWED_FILE_TYPES:
                if allowed == mime:
                    return True
                if allowed.endswith("/*") and mime.startswith(
                    allowed[:-2] + "/"
                ):
                    return True
            return False

        if not _matches(mime_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{mime_type}' is not allowed.",
            )

    def _virus_scan(self, content: bytes) -> None:
        if not self.settings.ENABLE_VIRUS_SCAN:
            return
        try:
            cd = clamd.ClamdUnixSocket()
            result = cd.instream(io.BytesIO(content))
            scan_status, reason = result.get("stream", ("OK", ""))
            if scan_status == "FOUND":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File failed virus scan: {reason}",
                )
        except HTTPException:
            raise
        except Exception as exc:
            self.logger.error(f"Virus scan error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Virus scanning failed. Upload rejected.",
            )

    def _compress_image(self, content: bytes, mime_type: str) -> bytes:
        fmt = _PIL_FORMAT.get(mime_type, "JPEG")
        img = Image.open(io.BytesIO(content))
        if fmt == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        kwargs: dict = {"format": fmt}
        if fmt in ("JPEG", "WEBP"):
            kwargs["quality"] = self.settings.IMAGE_COMPRESSION_QUALITY
            kwargs["optimize"] = True
        img.save(buf, **kwargs)
        return buf.getvalue()

    def _get_image_dimensions(self, content: bytes) -> dict:
        img = Image.open(io.BytesIO(content))
        return {"width": img.width, "height": img.height}

    def _make_thumbnail(
        self, content: bytes, size: tuple[int, int], mime_type: str
    ) -> bytes:
        fmt = _PIL_FORMAT.get(mime_type, "JPEG")
        img = Image.open(io.BytesIO(content))
        img.thumbnail(size, Image.Resampling.LANCZOS)
        if fmt == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(
            buf, format=fmt, quality=self.settings.IMAGE_COMPRESSION_QUALITY
        )
        return buf.getvalue()

    def _process_and_upload_image(
        self, content: bytes, mime_type: str, base_key: str, ext: str
    ) -> tuple[bytes, dict, str]:
        """
        Compress, make thumbnail + medium, upload derived sizes, return results.
        """
        content = self._compress_image(content, mime_type)
        dimensions = self._get_image_dimensions(content)

        thumb = self._make_thumbnail(content, THUMBNAIL_SIZE, mime_type)
        thumbnail_url = self._put_object(
            self.bucket_name, f"{base_key}_thumb{ext}", thumb, mime_type
        )
        medium = self._make_thumbnail(content, MEDIUM_SIZE, mime_type)
        self._put_object(
            self.bucket_name, f"{base_key}_medium{ext}", medium, mime_type
        )
        return content, dimensions, thumbnail_url

    async def upload_attachment(
        self, file: UploadFile, message_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        content = await file.read()
        mime_type = _guess_mime(file.filename or "file", file.content_type)
        file_type = _classify_mime(mime_type)

        self._validate_file(content, mime_type)
        self._virus_scan(content)

        ext = Path(file.filename or "file").suffix.lower()
        base_key = f"messages/{user_id}/{message_id}/{uuid.uuid4()}"

        thumbnail_url: str | None = None
        dimensions: dict | None = None

        if file_type == "image":
            content, dimensions, thumbnail_url = self._process_and_upload_image(
                content, mime_type, base_key, ext
            )

        file_url = self._put_object(
            self.bucket_name, f"{base_key}{ext}", content, mime_type
        )

        return {
            "file_type": file_type,
            "original_filename": file.filename or "file",
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "file_size": len(content),
            "mime_type": mime_type,
            "dimensions": dimensions,
            "metadata_": {
                "original_size": len(content),
                "resolutions": (
                    ["thumbnail", "medium", "full"]
                    if file_type == "image"
                    else None
                ),
            },
        }

    async def upload_attachment_chunked(
        self,
        chunk: bytes,
        upload_id: str,
        chunk_index: int,
        total_chunks: int,
        filename: str,
        mime_type: str,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        redis_client,
    ) -> dict | None:
        await redis_client.set(
            f"upload:{upload_id}:chunk:{chunk_index}",
            base64.b64encode(chunk).decode(),
            ex=3600,
        )

        received = []
        for i in range(total_chunks):
            val = await redis_client.get(f"upload:{upload_id}:chunk:{i}")
            if val:
                received.append((i, val))

        if len(received) < total_chunks:
            return None

        received.sort(key=lambda x: x[0])
        full_content = b"".join(base64.b64decode(v) for _, v in received)

        for i in range(total_chunks):
            await redis_client.delete(f"upload:{upload_id}:chunk:{i}")

        self._validate_file(full_content, mime_type)
        self._virus_scan(full_content)

        file_type = _classify_mime(mime_type)
        ext = Path(filename).suffix.lower()
        base_key = f"messages/{user_id}/{message_id}/{uuid.uuid4()}"

        thumbnail_url: str | None = None
        dimensions: dict | None = None

        if file_type == "image":
            (full_content, dimensions, thumbnail_url) = (
                self._process_and_upload_image(
                    full_content, mime_type, base_key, ext
                )
            )

        file_url = self._put_object(
            self.bucket_name, f"{base_key}{ext}", full_content, mime_type
        )

        return {
            "file_type": file_type,
            "original_filename": filename,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "file_size": len(full_content),
            "mime_type": mime_type,
            "dimensions": dimensions,
            "metadata_": {
                "upload_id": upload_id,
                "chunks": total_chunks,
                "resolutions": (
                    ["thumbnail", "medium", "full"]
                    if file_type == "image"
                    else None
                ),
            },
        }

    def delete_attachment(self, file_url: str) -> bool:
        object_name = self._object_name_from_url(file_url, self.bucket_name)
        return self._delete_object(self.bucket_name, object_name)

    @staticmethod
    def compute_total_chunks(file_size_bytes: int, chunk_size_mb: int) -> int:
        return math.ceil(file_size_bytes / (chunk_size_mb * 1024 * 1024))


avatar_storage = AvatarStorage()
media_storage = MediaStorage()
