import io
import json
import uuid
from logging import Logger
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.logger import get_logger


class MinioStorage:
    def __init__(
        self, settings: Settings | None = None, logger: Logger | None = None
    ):
        self.settings = settings or get_settings()
        self.logger = logger or get_logger()

        self.client = Minio(
            self.settings.MINIO_ENDPOINT,
            access_key=self.settings.MINIO_ACCESS_KEY,
            secret_key=self.settings.MINIO_SECRET_KEY,
            secure=self.settings.MINIO_SECURE,
        )
        self.bucket_name = self.settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(
                    self.bucket_name, location=self.settings.MINIO_REGION
                )
                self.logger.info(
                    f"Bucket '{self.bucket_name}' created successfully."
                )

                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                        }
                    ],
                }
                self.client.set_bucket_policy(
                    self.bucket_name, json.dumps(policy)
                )
                self.logger.info(
                    f"Public read policy set for bucket '{self.bucket_name}'."
                )
        except S3Error as e:
            self.logger.error(f"Error creating bucket: {e}")
            raise

    def _validate_image(self, file: UploadFile) -> bytes:
        """Validate image file type and size."""
        ext = Path(file.filename).suffix.lower()
        if ext not in self.settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Allowed formats: "
                + ", ".join(self.settings.ALLOWED_EXTENSIONS),
            )

        content = file.file.read()
        file.file.seek(0)  # Reset file pointer after reading

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

    def _get_public_url(self, object_name: str) -> str:
        """Generate public URL for object"""
        protocol = "https" if self.settings.MINIO_SECURE else "http"
        return f"{protocol}://{self.settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"

    async def upload_avatar(self, file: UploadFile, user_id: uuid.UUID) -> str:
        """Upload avatar to MinIO and return its public URL."""
        content = self._validate_image(file)
        ext = Path(file.filename).suffix.lower()
        filename = f"{user_id}/{uuid.uuid4()}{ext}"

        try:
            self.client.put_object(
                self.bucket_name,
                filename,
                io.BytesIO(content),
                length=len(content),
                content_type=file.content_type or "application/octet-stream",
            )
            self.logger.info(f"Image '{filename}' uploaded successfully.")

            # Generate public URL
            url = self._get_public_url(filename)
            return url
        except S3Error as e:
            self.logger.error(f"Error uploading image: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image. Please try again later.",
            )

    def delete_avatar(self, avatar_url: str) -> bool:
        """Delete avatar image from MinIO."""
        try:
            object_name = avatar_url.split(f"/{self.bucket_name}/")[-1]
            self.client.remove_object(self.bucket_name, object_name)
            self.logger.info(f"Image '{object_name}' deleted successfully.")
            return True
        except S3Error as e:
            self.logger.error(f"Error deleting image: {e}")
            return False


minio_storage = MinioStorage()
