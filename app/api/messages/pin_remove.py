from uuid import UUID

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversations import Conversation
from app.models.pinned_messages import PinnedMessage
from app.schemas.base import HTTPErrorResponse
from app.utils.get_active_message import get_active_message
from app.utils.require_participant import require_participant


@messages_router.delete(
    "/{message_id}/pin",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unpin a message in a group conversation",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def unpin_message(
    message_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Unpin a message from a group conversation. Admin only."""
    current_user = await get_current_user(credentials.credentials, db)
    message = await get_active_message(db, message_id)

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == message.conversation_id)
    )
    conv = conv_result.scalars().first()
    if not conv or conv.type != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only group conversations support pinned messages.",
        )

    participant = await require_participant(
        db, message.conversation_id, current_user.id
    )
    if participant.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can unpin messages.",
        )

    pin_result = await db.execute(
        select(PinnedMessage).where(PinnedMessage.message_id == message_id)
    )
    pin = pin_result.scalars().first()
    if not pin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message is not pinned.",
        )

    await db.delete(pin)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
