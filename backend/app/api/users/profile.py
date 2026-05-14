from uuid import UUID

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.users import User
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import UserPublicResponse
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession


@users_router.get(
    "/{user_id}",
    response_model=UserPublicResponse,
    summary="Get public user profile",
    description="Return the public profile of any active user by their UUID.",
    responses={
        200: {"description": "User profile returned successfully."},
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "model": HTTPErrorResponse,
        },
        403: {
            "description": "Forbidden - Caller account is not active",
            "model": HTTPErrorResponse,
        },
        404: {"description": "User not found", "model": HTTPErrorResponse},
    },
)
async def get_user_profile(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    user = await db.get(User, user_id)

    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user
