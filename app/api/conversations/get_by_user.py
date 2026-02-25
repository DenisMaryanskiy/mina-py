from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.conversations.router import conversations_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.conversation_participants import ConversationParticipant
from app.models.conversations import Conversation
from app.schemas.base import HTTPErrorResponse
from app.schemas.conversations import ConversationListItem


@conversations_router.get(
    "",
    response_model=list[ConversationListItem],
    summary="List user's conversations",
    responses={401: {"description": "Unauthorized", "model": HTTPErrorResponse}},
)
async def list_conversations(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationListItem]:
    """List all conversations the current user is a participant of."""
    current_user = await get_current_user(credentials.credentials, db)

    result = await db.execute(
        select(Conversation)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(ConversationParticipant.user_id == current_user.id)
        .order_by(
            Conversation.last_message_at.desc().nullslast(),
            Conversation.created_at.desc(),
        )
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Count participants
        count_result = await db.execute(
            select(func.count()).where(
                ConversationParticipant.conversation_id == conv.id
            )
        )
        participant_count = count_result.scalar() or 0
        items.append(
            ConversationListItem(
                id=conv.id,
                type=conv.type,
                name=conv.name,
                avatar_url=conv.avatar_url,
                created_by=conv.created_by,
                last_message_at=conv.last_message_at,
                participant_count=participant_count,
            )
        )
    return items
