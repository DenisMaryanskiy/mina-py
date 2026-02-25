from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversations import Conversation
from app.models.messages import Message
from app.schemas.base import HTTPErrorResponse
from app.schemas.messages import MessageCreate, MessageResponse
from app.utils.require_participant import require_participant


@messages_router.post(
    "/{conversation_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    current_user = await get_current_user(credentials.credentials, db)
    await require_participant(db, conversation_id, current_user.id)

    if data.reply_to_message_id:
        reply_result = await db.execute(
            select(Message).where(
                Message.id == data.reply_to_message_id,
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
        )
        if not reply_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply target message not found.",
            )

    now = datetime.now(timezone.utc)

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        metadata_=data.metadata,
        reply_to_message_id=data.reply_to_message_id,
        delivered_at=now,
    )
    db.add(message)

    # Update last_message_at on conversation
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalars().first()
    if conv:
        conv.last_message_at = now

    await db.commit()
    await db.refresh(message)
    return MessageResponse.model_validate(message)
