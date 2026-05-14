from app.api.users.router import users_router
from app.core.database import get_db
from app.core.dependencies import get_current_user, security
from app.models.users import User
from app.schemas.base import HTTPErrorResponse
from app.schemas.users import UserSearchResult
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@users_router.get(
    "/search",
    response_model=list[UserSearchResult],
    summary="Search users",
    description="Search active users by username or email prefix.",
    responses={
        200: {"description": "List of matching users (may be empty)."},
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
async def search_users(
    q: str = Query(
        ..., min_length=1, description="Search query (username or email)"
    ),
    limit: int = Query(
        default=20, ge=1, le=50, description="Max results to return"
    ),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    result = await db.execute(
        select(User)
        .where(
            (User.username.ilike(f"%{q}%") | User.email.ilike(f"%{q}%")),
            User.is_deleted.is_(False),
            User.is_active.is_(True),
        )
        .limit(limit)
    )
    return result.scalars().all()
