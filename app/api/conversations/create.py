from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.conversations.router import conversations_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.models.users import User
from app.schemas.base import HTTPErrorResponse
from app.schemas.conversations import ConversationCreate, ConversationResponse


@conversations_router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
    responses={
        400: {"description": "Bad request", "model": HTTPErrorResponse},
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        404: {"description": "User not found", "model": HTTPErrorResponse},
    },
)
async def create_conversation(
    data: ConversationCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """
    Create a new conversation.

    - **type**: 'direct' (1-on-1) or 'group'
    - **name**: Required for group conversations
    - **avatar_url**: Avatar used for group conversations
    - **participant_ids**: Users to include (creator is added automatically)
    """
    current_user = await get_current_user(credentials.credentials, db)

    if data.type == "direct":
        other_id = data.participant_ids[0]
        if current_user.id == other_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create a direct conversation with yourself.",
            )

        # Check if direct conversation already exists between the two users
        existing = await db.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                Conversation.type == "direct",
                ConversationParticipant.user_id == current_user.id,
            )
            .where(
                Conversation.id.in_(
                    select(ConversationParticipant.conversation_id).where(
                        ConversationParticipant.user_id == current_user.id
                    )
                )
            )
            .options(selectinload(Conversation.participants))
        )
        existing_conv = existing.scalars().first()
        if existing_conv:
            return ConversationResponse.model_validate(existing_conv)

    # Validate all participant users exist
    all_participant_ids = data.participant_ids
    if all_participant_ids:
        result = await db.execute(
            select(User.id).where(
                User.id.in_(all_participant_ids), User.is_deleted.is_(False)
            )
        )
        found_ids = {row[0] for row in result.fetchall()}
        missing = set(all_participant_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Users not found: {[str(m) for m in missing]}",
            )

    conversation = Conversation(
        type=data.type,
        name=data.name,
        avatar_url=data.avatar_url,
        created_by=current_user.id,
    )
    db.add(conversation)
    await db.flush()  # get ID

    # Add creator as admin
    creator_participant = ConversationParticipant(
        conversation_id=conversation.id, user_id=current_user.id, role="admin"
    )
    db.add(creator_participant)

    # Add other participants
    for user_id in all_participant_ids:
        if user_id != current_user.id:
            db.add(
                ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=user_id,
                    role="member",
                )
            )

    await db.commit()
    await db.refresh(conversation)

    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation.id)
        .options(selectinload(Conversation.participants))
    )
    conv = result.scalars().one()
    return ConversationResponse.model_validate(conv)
