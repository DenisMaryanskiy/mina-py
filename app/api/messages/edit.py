from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages.router import messages_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.schemas.base import HTTPErrorResponse
from app.schemas.messages import MessageEdit, MessageResponse
from app.utils.get_active_message import get_active_message


@messages_router.patch(
    "/{message_id}",
    response_model=MessageResponse,
    summary="Edit a message",
    responses={
        401: {"description": "Unauthorized", "model": HTTPErrorResponse},
        403: {"description": "Forbidden", "model": HTTPErrorResponse},
        404: {"description": "Not found", "model": HTTPErrorResponse},
    },
)
async def edit_message(
    message_id: UUID,
    data: MessageEdit,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Edit a message. Only the sender can edit their own messages."""
    current_user = await get_current_user(credentials.credentials, db)

    message = await get_active_message(db, message_id)

    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages.",
        )

    message.content = data.content
    message.is_edited = True
    await db.commit()
    await db.refresh(message)
    return MessageResponse.model_validate(message)
