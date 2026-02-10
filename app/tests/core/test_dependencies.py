import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.models.users import User


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(async_session: AsyncSession):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("invalid_token", async_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(
    async_session: AsyncSession, seed_user: User
):
    token = create_access_token(seed_user.id)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, async_session)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "User account is not active or deleted"
