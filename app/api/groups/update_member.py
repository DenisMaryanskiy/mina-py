from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.groups.router import groups_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.schemas.base import HTTPErrorResponse
from app.schemas.groups import MemberRoleUpdate
from app.schemas.participants import ParticipantResponse
from app.utils.require_participant import require_participant


@groups_router.patch(
    "/{group_id}/members/{user_id}",
    response_model=ParticipantResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a group member's role",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def update_member_role(
    group_id: UUID,
    user_id: UUID,
    data: MemberRoleUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ParticipantResponse:
    """Promote or demote a group member. Admin only."""
    current_user = await get_current_user(credentials.credentials, db)

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == group_id, Conversation.type == "group"
        )
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found."
        )

    requester = await require_participant(db, group_id, current_user.id)
    if requester.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update member roles.",
        )

    target_result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == group_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    target = target_result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this group.",
        )

    target.role = data.role
    await db.commit()
    await db.refresh(target)
    return ParticipantResponse.model_validate(target)
