from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.conversations.router import conversations_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.users import User
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse
from app.schemas.participants import AddParticipantsRequest, ParticipantResponse
from app.utils.require_participant import require_participant


@conversations_router.post(
    "/{conversation_id}/participants",
    response_model=list[ParticipantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add participants to a group conversation",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def add_participants(
    conversation_id: UUID,
    data: AddParticipantsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> list[ParticipantResponse]:
    """Add participants to a group conversation. Requester must be admin."""
    current_user = await get_current_user(credentials.credentials, db)

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    if conv.type != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add participants to a direct conversation.",
        )

    participant = await require_participant(db, conversation_id, current_user.id)

    if participant.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can add participants.",
        )

    new_participants = []
    for user_id in data.user_ids:
        # Check user exists
        user = await db.get(User, user_id)
        if not user or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found.",
            )
        # Check not already a participant
        existing = await db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        if existing.scalars().first():
            continue  # Skip already-added users silently

        p = ConversationParticipant(
            conversation_id=conversation_id, user_id=user_id, role="member"
        )
        db.add(p)
        new_participants.append(p)

    await db.commit()
    for p in new_participants:
        await db.refresh(p)

    return [ParticipantResponse.model_validate(p) for p in new_participants]


@conversations_router.delete(
    "/{conversation_id}/participants/{user_id}",
    response_model=GenericMessageResponse,
    summary="Remove a participant from a group conversation",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def remove_participant(
    conversation_id: UUID,
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> GenericMessageResponse:
    """
    Remove a participant.
    Admins can remove anyone; members can only remove themselves.
    """
    current_user = await get_current_user(credentials.credentials, db)

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalars().first()
    if not conv or conv.type != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only remove participants from group conversations.",
        )

    current_participant = await require_participant(
        db, conversation_id, current_user.id
    )

    if current_participant.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove other participants.",
        )

    target_result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    target = target_result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found in this conversation.",
        )

    await db.delete(target)
    await db.commit()
    return GenericMessageResponse(message="Participant removed successfully.")
