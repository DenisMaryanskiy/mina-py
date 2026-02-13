from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.core.storage import minio_storage
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import UserResponse


@users_router.post(
    "/avatar/upload",
    response_model=UserResponse,
    summary="Upload user avatar",
    description="Upload a new avatar image for the user.",
    responses={
        200: {"description": "User avatar uploaded successfully."},
        400: {
            "description": "Bad Request - Invalid file format or size",
            "model": HTTPErrorResponse,
        },
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "model": HTTPErrorResponse,
        },
        403: {
            "description": "Forbidden - User account is not active",
            "model": HTTPErrorResponse,
        },
        500: {
            "description": "Internal Server Error - Failed to upload avatar",
            "model": HTTPErrorResponse,
        },
    },
)
async def upload_avatar(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(credentials.credentials, db)

    avatar_url = await minio_storage.upload_avatar(file, user.id)

    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)

    return user


@users_router.post(
    "/avatar/delete",
    response_model=UserResponse,
    summary="Delete user avatar",
    description="Delete the user's avatar image.",
    responses={
        200: {"description": "User avatar deleted successfully."},
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "model": HTTPErrorResponse,
        },
        403: {
            "description": "Forbidden - User account is not active",
            "model": HTTPErrorResponse,
        },
        500: {
            "description": "Internal Server Error - Failed to delete avatar",
            "model": HTTPErrorResponse,
        },
    },
)
async def delete_avatar(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(credentials.credentials, db)

    if user.avatar_url:
        success = minio_storage.delete_avatar(user.avatar_url)
        if success:
            user.avatar_url = None
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete avatar from storage",
            )

    return user
