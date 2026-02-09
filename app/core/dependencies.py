from uuid import UUID

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.models.users import User

security = HTTPBearer()


async def get_current_user(token: str, db: AsyncSession) -> User:
    user_id = verify_token(token, token_type="access")

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

    return user
