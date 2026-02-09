from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from app.models.users import User
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import LoginResponse, TokenResponse, UserLogin

settings = get_settings()
security = HTTPBearer()


@users_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login a user",
    description="Authenticate a user and return an access token.",
    responses={
        200: {"description": "User authenticated successfully."},
        401: {
            "description": "Invalid email or password",
            "model": HTTPErrorResponse,
        },
        403: {
            "description": "User account is not active or deleted",
            "model": HTTPErrorResponse,
        },
    },
)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user using either email or username and
    return an access token.

    - **username_or_email**: The user's email or username for login.
    - **password**: The user's password for authentication.

    The endpoint will validate the provided credentials and return a JWT access
    token if authentication is successful. If the credentials are invalid or the
    user account is not active, appropriate error responses will be returned.
    """
    # Find user by email or username
    result = await db.execute(
        select(User).where(
            (User.email == login_data.username_or_email)
            | (User.username == login_data.username_or_email)
        )
    )
    user = result.scalars().one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, username or password",
        )

    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active or deleted",
        )

    user.last_seen = func.now()

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id.hex)
    refresh_token = create_refresh_token(user.id.hex)

    return LoginResponse(
        user=user,
        token=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@users_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Refresh the JWT access token using a valid refresh token.",
    responses={
        200: {"description": "Access token refreshed successfully."},
        401: {
            "description": "Invalid or expired refresh token",
            "model": HTTPErrorResponse,
        },
    },
)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh the JWT access token using a valid refresh token.

    - **Authorization**: The refresh token should be provided in the
        Authorization header as a Bearer token.

    The endpoint will validate the provided refresh token and return a new JWT
    access token if the refresh token is valid. If the refresh token is invalid
    or expired, an appropriate error response will be returned.
    """
    user_id = verify_token(credentials.credentials, token_type="refresh")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await db.get(User, UUID(user_id))

    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active or deleted",
        )

    access_token = create_access_token(user.id.hex)
    new_refresh_token = create_refresh_token(user.id.hex)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
