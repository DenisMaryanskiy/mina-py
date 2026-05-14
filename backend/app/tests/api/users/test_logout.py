from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.users import LoginResponse


@pytest.mark.asyncio
async def test_logout_success(
    async_client: AsyncClient, login_user: LoginResponse
):
    mock_redis = AsyncMock()
    mock_redis.is_token_denied = AsyncMock(return_value=False)
    mock_redis.denylist_token = AsyncMock(return_value=True)

    with (
        patch("app.core.dependencies.get_redis", return_value=mock_redis),
        patch("app.api.users.logout.get_redis", return_value=mock_redis),
    ):
        response = await async_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    mock_redis.denylist_token.assert_called_once()


@pytest.mark.asyncio
async def test_logout_token_revoked_on_reuse(
    async_client: AsyncClient, login_user: LoginResponse
):
    """After logout the same token must be rejected on subsequent requests."""
    denied = {"value": False}

    async def is_denied(_token: str) -> bool:
        return denied["value"]

    async def denylist(_token: str, _ttl: int) -> bool:
        denied["value"] = True
        return True

    mock_redis = AsyncMock()
    mock_redis.is_token_denied = is_denied
    mock_redis.denylist_token = denylist

    with (
        patch("app.core.dependencies.get_redis", return_value=mock_redis),
        patch("app.api.users.logout.get_redis", return_value=mock_redis),
    ):
        logout_resp = await async_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )
        assert logout_resp.status_code == 200

        reuse_resp = await async_client.get(
            "/api/v1/users/search",
            params={"q": "test"},
            headers={"Authorization": f"Bearer {login_user.token.access_token}"},
        )

    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Token has been revoked"


@pytest.mark.asyncio
async def test_logout_unauthenticated(async_client: AsyncClient):
    response = await async_client.post("/api/v1/users/logout")
    assert response.status_code == 401
