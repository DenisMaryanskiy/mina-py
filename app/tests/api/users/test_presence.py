from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_user_presence_online(
    async_client: AsyncClient, test_token: str, test_user_id: str
):
    with patch(
        "app.api.users.presence.connection_manager.get_user_presence",
        new_callable=AsyncMock,
        return_value={"status": "online", "last_seen": "2026-02-15T10:00:00Z"},
    ):
        response = await async_client.get(
            f"/api/v1/users/{test_user_id}/presence",
            headers={"Authorization": f"Bearer {test_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == test_user_id
    assert body["status"] == "online"
    assert body["last_seen"] == "2026-02-15T10:00:00Z"


@pytest.mark.asyncio
async def test_bulk_presence_returns_all_users(
    async_client: AsyncClient, test_token: str
):
    user_ids = [
        "123e4567-e89b-12d3-a456-426614174000",
        "223e4567-e89b-12d3-a456-426614174001",
    ]
    mock_bulk = [
        {
            "user_id": user_ids[0],
            "status": "online",
            "last_seen": "2026-02-15T10:00:00+00:00",
        },
        {"user_id": user_ids[1], "status": "offline", "last_seen": None},
    ]

    with patch(
        "app.api.users.presence.connection_manager.get_bulk_presence",
        new_callable=AsyncMock,
        return_value=mock_bulk,
    ):
        response = await async_client.post(
            "/users/presence/bulk",
            json={"user_ids": user_ids},
            headers={"Authorization": f"Bearer {test_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "presence" in body
    assert len(body["presence"]) == 2
    assert body["presence"][0]["status"] == "online"
    assert body["presence"][1]["status"] == "offline"
