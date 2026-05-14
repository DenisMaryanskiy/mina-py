from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def get_active_message(db: AsyncSession, message_id: UUID) -> Message:
    result = await db.execute(
        select(Message).where(
            Message.id == message_id, Message.is_deleted.is_(False)
        )
    )
    message = result.scalars().first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    return message
