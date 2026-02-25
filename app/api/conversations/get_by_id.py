from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.conversations.router import conversations_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversations import Conversation
from app.schemas.base import HTTPErrorResponse
from app.schemas.conversations import ConversationResponse
from app.utils.require_participant import require_participant


@conversations_router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def get_conversation(
    conversation_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get details for a conversation the current user participates in."""
    current_user = await get_current_user(credentials.credentials, db)

    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.participants))
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    await require_participant(db, conversation_id, current_user.id)

    return ConversationResponse.model_validate(conv)
