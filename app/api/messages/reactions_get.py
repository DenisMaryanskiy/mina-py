from collections import defaultdict
from uuid import UUID

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.reactions import MessageReaction
from app.schemas.base import HTTPErrorResponse
from app.schemas.reactions import ReactionSummaryItem, ReactionSummaryResponse
from app.utils.get_active_message import get_active_message
from app.utils.require_participant import require_participant


@messages_router.get(
    "/{message_id}/reactions",
    response_model=ReactionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reactions for a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Message not found", "model": HTTPErrorResponse},
    },
)
async def get_reactions(
    message_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ReactionSummaryResponse:
    current_user = await get_current_user(credentials.credentials, db)
    message = await get_active_message(db, message_id)
    await require_participant(db, message.conversation_id, current_user.id)

    result = await db.execute(
        select(MessageReaction).where(MessageReaction.message_id == message_id)
    )
    reactions = result.scalars().all()

    groups: dict[str, list[UUID]] = defaultdict(list)
    for reaction in reactions:
        groups[reaction.emoji].append(reaction.user_id)

    items = [
        ReactionSummaryItem(emoji=emoji, count=len(user_ids), user_ids=user_ids)
        for emoji, user_ids in groups.items()
    ]
    return ReactionSummaryResponse(message_id=message_id, reactions=items)
