from uuid import UUID

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.reactions import MessageReaction
from app.schemas.base import HTTPErrorResponse
from app.utils.get_active_message import get_active_message
from app.utils.require_participant import require_participant


@messages_router.delete(
    "/{message_id}/reactions/{emoji}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a reaction from a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {
            "description": "Message or reaction not found",
            "model": HTTPErrorResponse,
        },
    },
)
async def remove_reaction(
    message_id: UUID,
    emoji: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Response:
    current_user = await get_current_user(credentials.credentials, db)
    message = await get_active_message(db, message_id)
    await require_participant(db, message.conversation_id, current_user.id)

    result = await db.execute(
        select(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == current_user.id,
            MessageReaction.emoji == emoji,
        )
    )
    reaction = result.scalars().first()
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reaction not found."
        )

    await db.delete(reaction)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
