from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_participants import ConversationParticipant


async def require_participant(
    db: AsyncSession, conversation_id: UUID, user_id: UUID
) -> ConversationParticipant:
    """Return the ConversationParticipant row or raise 403."""
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    participant = result.scalars().first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this conversation.",
        )
    return participant
