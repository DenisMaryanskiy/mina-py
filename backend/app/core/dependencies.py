from uuid import UUID

from fastapi import HTTPException, WebSocket, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.core.security import verify_token
from app.models.users import User

logger = get_logger()
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active or deleted",
        )

    return user


async def get_user_from_token_ws(websocket: WebSocket) -> str | None:
    """
    Extract and validate user ID from WebSocket query params.

    :param websocket: WebSocket connection

    :return: User ID if valid token, None otherwise
    """
    try:
        # Get token from query params
        token = websocket.query_params.get("token")
        if not token:
            return None

        # Verify token and get user ID
        user_id = verify_token(token, token_type="access")
        return user_id

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None
