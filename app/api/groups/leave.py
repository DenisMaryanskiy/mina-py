from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.groups.router import groups_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse
from app.utils.require_participant import require_participant


@groups_router.post(
    "/{group_id}/leave",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Leave a group",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Group not found", "model": HTTPErrorResponse},
    },
)
async def leave_group(
    group_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> GenericMessageResponse:
    """
    Leave a group conversation.

    - Admins must transfer admin role to another member before leaving
      (unless they are the last person in the group).
    - If the requester is the last person, the group is deleted.
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

    my_participant = await require_participant(db, group_id, current_user.id)

    # Count total participants and admins
    total_count_result = await db.execute(
        select(func.count()).where(
            ConversationParticipant.conversation_id == group_id
        )
    )
    total_count = total_count_result.scalar_one()

    if my_participant.role == "admin":
        if total_count == 1:
            # Last person — delete the entire conversation
            await db.delete(conv)
            await db.commit()
            return GenericMessageResponse(
                message="Left group successfully. Group deleted."
            )

        # Check if there is another admin
        other_admin_result = await db.execute(
            select(func.count()).where(
                ConversationParticipant.conversation_id == group_id,
                ConversationParticipant.role == "admin",
                ConversationParticipant.user_id != current_user.id,
            )
        )
        other_admin_count = other_admin_result.scalar_one()

        if other_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "You are the last admin. "
                    "Transfer admin role to another member before leaving."
                ),
            )

    await db.delete(my_participant)
    await db.commit()
    return GenericMessageResponse(message="Left group successfully.")
