from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.groups.router import groups_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversations import Conversation
from app.schemas.base import HTTPErrorResponse
from app.schemas.conversations import ConversationResponse
from app.schemas.groups import GroupUpdate
from app.utils.require_participant import require_participant


@groups_router.patch(
    "/{group_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update group info",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Group not found", "model": HTTPErrorResponse},
    },
)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Update group name, avatar, description, visibility, or settings.

    Admin only.
    """
    current_user = await get_current_user(credentials.credentials, db)

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == group_id, Conversation.type == "group"
        )
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found."
        )

    participant = await require_participant(db, group_id, current_user.id)
    if participant.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update group info.",
        )

    # Apply only the fields that were explicitly provided (non-None)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conv, field, value)

    await db.commit()

    refreshed = await db.execute(
        select(Conversation)
        .where(Conversation.id == group_id)
        .options(selectinload(Conversation.participants))
    )
    return ConversationResponse.model_validate(refreshed.scalars().one())
