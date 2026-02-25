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
from app.schemas.messages import MessageResponse, PaginatedMessages
from app.utils.require_participant import require_participant


@messages_router.get(
    "/{conversation_id}",
    response_model=PaginatedMessages,
    summary="Get message history",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def get_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search within messages"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> PaginatedMessages:
    """
    Retrieve paginated message history for a conversation.
    Supports optional full-text search via `search` query param.
    """
    current_user = await get_current_user(credentials.credentials, db)
    await require_participant(db, conversation_id, current_user.id)

    base_query = select(Message).where(
        Message.conversation_id == conversation_id, Message.is_deleted.is_(False)
    )

    if search:
        base_query = base_query.where(Message.content.ilike(f"%{search}%"))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    messages_result = await db.execute(
        base_query.order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    messages = messages_result.scalars().all()

    return PaginatedMessages(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + page_size < total,
        has_prev=page > 1,
    )
