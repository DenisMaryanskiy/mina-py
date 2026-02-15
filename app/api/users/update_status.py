from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import UserResponse, UserUpdateStatus


@users_router.post(
    "/status/update",
    response_model=UserResponse,
    summary="Update user status",
    description="Update user profile with a new status message.",
    responses={
        200: {"description": "User profile status updated successfully."},
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "model": HTTPErrorResponse,
        },
        403: {
            "description": "Forbidden - User account is not active",
            "model": HTTPErrorResponse,
        },
    },
)
async def enhance_user_profile(
    enhance_data: UserUpdateStatus,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the user's profile status with additional information.

    - **status**: A short status message or bio for the user's profile.

    The endpoint will update the user's profile with the provided information and
    return the updated user data. If the token is invalid or the user account is
    not active, appropriate error responses will be returned.
    """
    user = await get_current_user(credentials.credentials, db)

    user.status = enhance_data.status

    await db.commit()
    await db.refresh(user)

    return user
