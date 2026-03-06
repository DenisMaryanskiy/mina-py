from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttachmentResponse(BaseModel):
    id: UUID = Field(..., description="Unique attachment ID")
    message_id: UUID = Field(..., description="Parent message ID")
    file_type: str = Field(
        ..., description="Canonical type: image, video, audio, document"
    )
    original_filename: str = Field(..., description="Original file name")
    file_url: str = Field(..., description="Full-resolution URL")
    thumbnail_url: str | None = Field(
        None, description="Thumbnail URL (images only)"
    )
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str | None = Field(None, description="MIME type")
    duration: int | None = Field(
        None, description="Duration in seconds (audio/video)"
    )
    dimensions: dict | None = Field(
        None, description='Image dimensions e.g. {"width": 1920, "height": 1080}'
    )
    metadata: dict | None = Field(None, alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChunkedUploadInit(BaseModel):
    upload_id: str = Field(..., description="Server-generated upload session ID")
    total_chunks: int = Field(..., description="Total number of expected chunks")
    chunk_size_bytes: int = Field(
        ..., description="Recommended chunk size in bytes"
    )


class ChunkedUploadStatus(BaseModel):
    upload_id: str
    chunks_received: int
    total_chunks: int
    complete: bool
    attachment: AttachmentResponse | None = None
