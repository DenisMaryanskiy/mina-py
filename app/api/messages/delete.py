from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse
from app.utils.get_active_message import get_active_message


@messages_router.delete(
    "/{message_id}",
    response_model=GenericMessageResponse,
    summary="Delete a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def delete_message(
    message_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> GenericMessageResponse:
    """Soft-delete a message. Only the sender can delete their own messages."""
    current_user = await get_current_user(credentials.credentials, db)

    message = await get_active_message(db, message_id)

    if message.sender_id != current_user.id:
        # Also allow conversation admins to delete
        participant_result = await db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id
                == message.conversation_id,
                ConversationParticipant.user_id == current_user.id,
            )
        )
        participant = participant_result.scalars().first()
        if not participant or participant.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages.",
            )

    message.is_deleted = True
    message.content = None  # Clear content for privacy
    await db.commit()
    return GenericMessageResponse(message="Message deleted successfully.")
