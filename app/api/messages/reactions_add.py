from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.reactions import MessageReaction
from app.schemas.base import HTTPErrorResponse
from app.schemas.reactions import ReactionCreate, ReactionResponse
from app.utils.get_active_message import get_active_message
from app.utils.require_participant import require_participant


@messages_router.post(
    "/{message_id}/reactions",
    response_model=ReactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a reaction to a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Message not found", "model": HTTPErrorResponse},
        409: {
            "description": "Reaction already exists",
            "model": HTTPErrorResponse,
        },
    },
)
async def add_reaction(
    message_id: UUID,
    data: ReactionCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ReactionResponse:
    current_user = await get_current_user(credentials.credentials, db)
    message = await get_active_message(db, message_id)
    await require_participant(db, message.conversation_id, current_user.id)

    reaction = MessageReaction(
        message_id=message_id, user_id=current_user.id, emoji=data.emoji
    )
    db.add(reaction)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reacted with this emoji.",
        )

    await db.commit()
    await db.refresh(reaction)
    return ReactionResponse.model_validate(reaction)
