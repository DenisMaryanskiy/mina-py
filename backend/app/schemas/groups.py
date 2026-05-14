from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=1000)
    is_public: bool | None = None
    max_participants: int | None = Field(None, ge=2, le=10000)
    settings: dict | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Group Name",
                "description": "Our awesome group",
                "is_public": True,
                "max_participants": 500,
            }
        }
    )


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "member"]

    model_config = ConfigDict(json_schema_extra={"example": {"role": "admin"}})


class PinnedMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    message_id: UUID
    pinned_by: UUID | None
    pinned_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "conversation_id": "223e4567-e89b-12d3-a456-426614174001",
                "message_id": "323e4567-e89b-12d3-a456-426614174002",
                "pinned_by": "423e4567-e89b-12d3-a456-426614174003",
                "pinned_at": "2026-03-25T10:00:00Z",
            }
        },
    )
