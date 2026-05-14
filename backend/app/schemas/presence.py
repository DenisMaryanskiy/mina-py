from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserPresenceResponse(BaseModel):
    """Schema for user presence data."""

    user_id: str = Field(..., description="User ID")
    status: Literal["online", "offline", "away"] = Field(
        ..., description="Current presence status"
    )
    last_seen: datetime | None = Field(
        None, description="Timestamp of last activity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "online",
                "last_seen": "2026-02-15T10:00:00Z",
            }
        }
    )


class BulkPresenceRequest(BaseModel):
    """Schema for bulk presence query."""

    user_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of user IDs to query presence for",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "223e4567-e89b-12d3-a456-426614174001",
                ]
            }
        }
    )


class BulkPresenceResponse(BaseModel):
    """Schema for bulk presence response."""

    presence: list[UserPresenceResponse] = Field(
        ..., description="List of user presence data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "presence": [
                    {
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "online",
                        "last_seen": "2026-02-15T10:00:00Z",
                    },
                    {
                        "user_id": "223e4567-e89b-12d3-a456-426614174001",
                        "status": "offline",
                        "last_seen": "2026-02-14T08:30:00Z",
                    },
                ]
            }
        }
    )


# ================================
# WebSocket event schemas (for documentation purposes)
# ================================


class PresenceUpdateEvent(BaseModel):
    """WebSocket presence_update event payload."""

    type: Literal["presence_update"] = "presence_update"
    user_id: str = Field(..., description="User whose presence changed")
    status: Literal["online", "offline", "away"] = Field(
        ..., description="New presence status"
    )
    last_seen: str = Field(..., description="ISO 8601 timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "presence_update",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "online",
                "last_seen": "2026-02-15T10:00:00Z",
            }
        }
    )


class TypingEvent(BaseModel):
    """WebSocket typing event payload."""

    type: Literal["typing"] = "typing"
    conversation_id: str = Field(..., description="Conversation ID")
    user_id: str = Field(..., description="User who is typing")
    is_typing: bool = Field(..., description="True if user is typing")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "typing",
                "conversation_id": "abc12345-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_typing": True,
            }
        }
    )
