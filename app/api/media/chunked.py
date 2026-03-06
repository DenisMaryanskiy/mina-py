import uuid

from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.media.router import media_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.core.redis import get_redis
from app.core.storage import media_storage
from app.models.attachments import MessageAttachment
from app.models.messages import Message
from app.schemas.attachments import (
    AttachmentResponse,
    ChunkedUploadInit,
    ChunkedUploadStatus,
)
from app.schemas.base import HTTPErrorResponse
from app.utils.require_participant import require_participant


@media_router.post(
    "/chunked/init",
    response_model=ChunkedUploadInit,
    status_code=status.HTTP_200_OK,
    summary="Initialise a chunked upload session",
    responses={401: {"description": "Unauthorized", "model": HTTPErrorResponse}},
)
async def init_chunked_upload(
    file_size: int = Form(..., description="Total file size in bytes", gt=0),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ChunkedUploadInit:
    await get_current_user(credentials.credentials, db)

    chunk_size_mb = media_storage.settings.CHUNK_SIZE_MB
    total_chunks = media_storage.compute_total_chunks(file_size, chunk_size_mb)
    upload_id = str(uuid.uuid4())

    return ChunkedUploadInit(
        upload_id=upload_id,
        total_chunks=total_chunks,
        chunk_size_bytes=chunk_size_mb * 1024 * 1024,
    )


@media_router.post(
    "/chunked/chunk",
    response_model=ChunkedUploadStatus,
    status_code=status.HTTP_200_OK,
    summary="Upload a single chunk",
    description=(
        "Send chunks in order. When the final chunk is received "
        "the server assembles the file and returns the completed attachment."
    ),
    responses={
        400: {
            "description": "Invalid chunk or file",
            "model": HTTPErrorResponse,
        },
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        404: {"description": "Message not found", "model": HTTPErrorResponse},
    },
)
async def upload_chunk(
    upload_id: str = Form(
        ..., description="Upload session ID from /chunked/init"
    ),
    chunk_index: int = Form(..., description="Zero-based chunk index", ge=0),
    total_chunks: int = Form(..., description="Total number of chunks", gt=0),
    message_id: uuid.UUID = Form(..., description="Message to attach file to"),
    filename: str = Form(..., description="Original filename"),
    mime_type: str = Form(..., description="MIME type of the file"),
    chunk: UploadFile = File(..., description="Chunk binary data"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ChunkedUploadStatus:
    current_user = await get_current_user(credentials.credentials, db)

    # Verify message exists and user is participant
    result = await db.execute(
        select(Message).where(
            Message.id == message_id, Message.is_deleted.is_(False)
        )
    )
    message = result.scalars().first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    await require_participant(db, message.conversation_id, current_user.id)

    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only attach files to your own messages.",
        )

    chunk_content = await chunk.read()
    redis = get_redis()

    attachment_data = await media_storage.upload_attachment_chunked(
        chunk=chunk_content,
        upload_id=upload_id,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        filename=filename,
        mime_type=mime_type,
        message_id=message_id,
        user_id=current_user.id,
        redis_client=redis,
    )

    if attachment_data is None:
        # Count received chunks to report progress
        chunks_received = 0
        for i in range(total_chunks):
            val = await redis.get(f"upload:{upload_id}:chunk:{i}")
            if val:
                chunks_received += 1

        return ChunkedUploadStatus(
            upload_id=upload_id,
            chunks_received=chunks_received,
            total_chunks=total_chunks,
            complete=False,
            attachment=None,
        )

    # All chunks received – persist to DB
    attachment = MessageAttachment(
        message_id=message_id,
        file_type=attachment_data["file_type"],
        original_filename=attachment_data["original_filename"],
        file_url=attachment_data["file_url"],
        thumbnail_url=attachment_data["thumbnail_url"],
        file_size=attachment_data["file_size"],
        mime_type=attachment_data["mime_type"],
        dimensions=attachment_data["dimensions"],
        metadata_=attachment_data["metadata_"],
    )
    db.add(attachment)
    await db.flush()
    await db.refresh(attachment)
    await db.commit()

    return ChunkedUploadStatus(
        upload_id=upload_id,
        chunks_received=total_chunks,
        total_chunks=total_chunks,
        complete=True,
        attachment=AttachmentResponse.model_validate(attachment),
    )
