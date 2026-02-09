from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import UserProfileEnhance, UserResponse


@users_router.post(
    "/enhance",
    response_model=UserResponse,
    summary="Enhance user profile",
    description="Enhance the user's profile with additional information.",
    responses={
        200: {"description": "User profile enhanced successfully."},
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "model": HTTPErrorResponse,
        },
    },
)
async def enhance_user_profile(
    enhance_data: UserProfileEnhance,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Enhance the user's profile with additional information.

    - **full_name**: The user's full name to enhance the profile.
    - **bio**: A short biography or description about the user.

    The endpoint will update the user's profile with the provided information and
    return the updated user data. If the token is invalid or the user account is
    not active, appropriate error responses will be returned.
    """
    user = await get_current_user(credentials.credentials, db)

    user.avatar_url = enhance_data.avatar_url
    user.status = enhance_data.status

    await db.commit()
    await db.refresh(user)

    return user
