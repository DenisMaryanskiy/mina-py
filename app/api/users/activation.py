from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.models.users import User
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse


@users_router.get(
    "/activate/{activation_token}",
    status_code=status.HTTP_200_OK,
    response_model=GenericMessageResponse,
    summary="Activate a user account",
    description="Activate a user account using the provided activation token.",
    responses={
        200: {
            "description": "User activated successfully.",
            "model": GenericMessageResponse,
        },
        400: {
            "description": (
                "Invalid activation token or account already activated."
            ),
            "model": HTTPErrorResponse,
        },
    },
)
async def activate_user(
    activation_token: str, db: AsyncSession = Depends(get_db)
) -> GenericMessageResponse:
    """
    Activate a user account using the provided activation token.
    - **activation_token**: The token sent to the user for account activation.
    """

    result = await db.execute(
        select(User).where(User.activation_token == activation_token)
    )
    user = result.scalars().one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already activated.",
        )

    user.is_active = True
    user.activation_token = ""

    await db.commit()
    await db.refresh(user)

    return GenericMessageResponse(message="Account activated successfully.")
