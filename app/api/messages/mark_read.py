from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse
from app.utils.get_active_message import get_active_message
from app.utils.require_participant import require_participant


@messages_router.post(
    "/{message_id}/read",
    response_model=GenericMessageResponse,
    summary="Mark message as read",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def mark_message_read(
    message_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> GenericMessageResponse:
    """
    Mark a message as read and update the participant's last_read_message_id.
    """
    current_user = await get_current_user(credentials.credentials, db)

    message = await get_active_message(db, message_id)

    participant = await require_participant(
        db, message.conversation_id, current_user.id
    )

    # Update message read_at if not already set
    if not message.read_at:
        message.read_at = datetime.now(timezone.utc)

    # Update participant's last_read pointer
    participant.last_read_message_id = message.id

    await db.commit()
    return GenericMessageResponse(message="Message marked as read.")
