from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.media.router import media_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.core.storage import media_storage
from app.models.attachments import MessageAttachment
from app.models.messages import Message
from app.schemas.attachments import AttachmentResponse
from app.schemas.base import HTTPErrorResponse
from app.utils.require_participant import require_participant


@media_router.post(
    "/upload/{message_id}",
    response_model=list[AttachmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload file attachments to a message",
    description=(
        "Upload one or more files (images, video, audio, documents) "
        "and attach them to an existing message. "
        "Images are compressed and thumbnails are generated automatically."
    ),
    responses={
        400: {
            "description": "Invalid file or file too large",
            "model": HTTPErrorResponse,
        },
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Message not found", "model": HTTPErrorResponse},
    },
)
async def upload_attachments(
    message_id: UUID,
    files: list[UploadFile] = File(
        ..., description="One or more files to upload"
    ),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentResponse]:
    current_user = await get_current_user(credentials.credentials, db)

    # Fetch message and verify ownership + participant status
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

    created: list[AttachmentResponse] = []

    for file in files:
        data = await media_storage.upload_attachment(
            file=file, message_id=message_id, user_id=current_user.id
        )

        attachment = MessageAttachment(
            message_id=message_id,
            file_type=data["file_type"],
            original_filename=data["original_filename"],
            file_url=data["file_url"],
            thumbnail_url=data["thumbnail_url"],
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            dimensions=data["dimensions"],
            metadata_=data["metadata_"],
        )
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        created.append(AttachmentResponse.model_validate(attachment))

    await db.commit()
    return created
