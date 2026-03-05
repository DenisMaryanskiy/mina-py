from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.api.users.router import users_router
from app.core.dependencies import security
from app.core.websocket import connection_manager
from app.schemas.base import HTTPErrorResponse
from app.schemas.presence import (
    BulkPresenceRequest,
    BulkPresenceResponse,
    UserPresenceResponse,
)


@users_router.get(
    "/{user_id}/presence",
    response_model=UserPresenceResponse,
    summary="Get user presence",
    description=(
        "Return the current presence status (online / offline / away) and "
        "the ``last_seen`` timestamp for any user.  "
        "The data is served from Redis and reflects real-time state."
    ),
    responses={
        200: {"description": "User presence data"},
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
async def get_user_presence(
    user_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Retrieve the real-time presence status of a specific user.

    - **user_id**: UUID of the user whose presence is being queried.

    The caller must supply a valid JWT access token.  No DB lookup is
    performed – presence is read directly from Redis so the response is
    near-instant even under heavy load.
    """
    presence = await connection_manager.get_user_presence(user_id)

    last_seen_raw = presence.get("last_seen")

    return UserPresenceResponse(
        user_id=user_id,
        status=presence.get("status", "offline"),
        last_seen=last_seen_raw,
    )


@users_router.post(
    "/presence/bulk",
    response_model=BulkPresenceResponse,
    summary="Get bulk user presence",
    description=(
        "Return presence data for up to 100 users in a single request.  "
        "Useful for populating contact lists or conversation participant lists."
    ),
    responses={
        200: {"description": "Bulk presence data"},
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
async def get_bulk_presence(
    request: BulkPresenceRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Retrieve presence data for multiple users at once.

    - **user_ids**: List of user UUID strings (max 100).

    Returns a list of presence objects in the same order as the request.
    Users with no presence record in Redis are returned with
    ``status: "offline"`` and ``last_seen: null``.
    """
    results = await connection_manager.get_bulk_presence(request.user_ids)

    presence_list = [
        UserPresenceResponse(
            user_id=item["user_id"],
            status=item["status"],
            last_seen=item["last_seen"],
        )
        for item in results
    ]

    return BulkPresenceResponse(presence=presence_list)
