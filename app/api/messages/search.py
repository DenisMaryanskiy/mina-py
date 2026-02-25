from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.messages import Message
from app.schemas.base import HTTPErrorResponse
from app.schemas.messages import MessageResponse, MessageSearchResponse
from app.utils.require_participant import require_participant


@messages_router.get(
    "/{conversation_id}/search",
    response_model=MessageSearchResponse,
    summary="Search within a conversation",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
    },
)
async def search_messages(
    conversation_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> MessageSearchResponse:
    """Search messages within a conversation."""
    current_user = await get_current_user(credentials.credentials, db)
    await require_participant(db, conversation_id, current_user.id)

    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.is_deleted.is_(False),
            Message.content.ilike(f"%{q}%"),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).where(
            Message.conversation_id == conversation_id,
            Message.is_deleted.is_(False),
            Message.content.ilike(f"%{q}%"),
        )
    )
    total = count_result.scalar() or 0

    return MessageSearchResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        query=q,
    )
