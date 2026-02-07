from fastapi import BackgroundTasks, Depends, HTTPException, status
from fastapi_mail import FastMail
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.email import get_mailer_config, prepare_message
from app.models.users import User
from app.schemas.base import MessageResponse


@users_router.post(
    "/resend-activation",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend account activation email",
    description="""Resend the activation email to a user who
    has not yet activated their account.""",
)
async def resend_activation_email(
    username: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Resend the activation email to a user who has not activated their account.

    - **username**: The username of the user to resend the activation email to.
    """

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this username does not exist.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already activated.",
        )

    mailer_config = get_mailer_config()
    fm = FastMail(mailer_config)

    message = prepare_message(user.email, user.activation_token)

    background_tasks.add_task(fm.send_message, message)

    return MessageResponse(
        message="Activation email has been resent. Please check your inbox."
    )
