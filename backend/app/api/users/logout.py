from datetime import datetime, timezone

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.core.redis import get_redis
from app.core.security import decode_token
from app.schemas.base import GenericMessageResponse, HTTPErrorResponse
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession


@users_router.post(
    "/logout",
    response_model=GenericMessageResponse,
    summary="Logout",
    description="Invalidate the current access token via Redis denylist.",
    responses={
        200: {"description": "Logged out successfully."},
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
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    token = credentials.credentials
    payload = decode_token(token)
    exp = payload.get("exp", 0)
    ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)

    redis = get_redis()
    await redis.denylist_token(token, ttl)

    return GenericMessageResponse(message="Logged out successfully")
