from uuid import UUID

from fastapi import Depends, HTTPException, status
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


@media_router.get(
    "/attachments/{message_id}",
    response_model=list[AttachmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List attachments for a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Message not found", "model": HTTPErrorResponse},
    },
)
async def get_attachments(
    message_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> list[AttachmentResponse]:
    current_user = await get_current_user(credentials.credentials, db)

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

    att_result = await db.execute(
        select(MessageAttachment).where(
            MessageAttachment.message_id == message_id
        )
    )
    attachments = att_result.scalars().all()
    return [AttachmentResponse.model_validate(a) for a in attachments]


@media_router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attachment",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Attachment not found", "model": HTTPErrorResponse},
    },
)
async def delete_attachment(
    attachment_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> None:
    current_user = await get_current_user(credentials.credentials, db)

    att_result = await db.execute(
        select(MessageAttachment).where(MessageAttachment.id == attachment_id)
    )
    attachment = att_result.scalars().first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found."
        )

    # Fetch parent message to confirm participant + ownership
    msg_result = await db.execute(
        select(Message).where(Message.id == attachment.message_id)
    )
    message = msg_result.scalars().first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Parent message not found. Data integrity issue.",
        )

    await require_participant(db, message.conversation_id, current_user.id)

    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete attachments from your own messages.",
        )

    # Remove from MinIO
    media_storage.delete_attachment(attachment.file_url)
    if attachment.thumbnail_url:
        media_storage.delete_attachment(attachment.thumbnail_url)

    await db.delete(attachment)
    await db.commit()
