from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.conversations.helpers import require_participant
from app.api.conversations.router import conversations_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversations import Conversation
from app.schemas.base import HTTPErrorResponse, MessageResponse


@conversations_router.delete(
    "/{conversation_id}",
    response_model=MessageResponse,
    summary="Leave or delete a conversation",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def delete_or_leave_conversation(
    conversation_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Leave a conversation. If the user is the creator and it's a group,
    the conversation is deleted. For direct conversations, the user just leaves.
    """
    current_user = await get_current_user(credentials.credentials, db)

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    participant = await require_participant(db, conversation_id, current_user.id)

    if conv.created_by == current_user.id and conv.type == "group":
        # Creator deletes the whole conversation
        await db.delete(conv)
        await db.commit()
        return MessageResponse(message="Conversation deleted successfully.")
    else:
        # Other participants just leave
        await db.delete(participant)
        await db.commit()
        return MessageResponse(message="Left conversation successfully.")
