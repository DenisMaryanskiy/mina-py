from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParticipantResponse(BaseModel):
    """Schema for participant entity response."""

    id: UUID = Field(
        ..., description="Unique identifier of the participant record"
    )
    conversation_id: UUID = Field(
        ..., description="Conversation this participant belongs to"
    )
    user_id: UUID = Field(..., description="User ID of the participant")
    role: str = Field(..., description="Participant role: 'admin' or 'member'")
    joined_at: datetime = Field(
        ..., description="Timestamp when the user joined the conversation"
    )
    last_read_message_id: UUID | None = Field(
        None, description="ID of the last message the user has read"
    )
    muted_until: datetime | None = Field(
        None, description="Timestamp until which notifications are muted"
    )
    notification_settings: dict | None = Field(
        None,
        description="Per-user notification preferences for this conversation",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "conversation_id": "223e4567-e89b-12d3-a456-426614174001",
                "user_id": "323e4567-e89b-12d3-a456-426614174002",
                "role": "member",
                "joined_at": "2026-02-01T10:00:00Z",
                "last_read_message_id": None,
                "muted_until": None,
                "notification_settings": None,
            }
        },
    )


class AddParticipantsRequest(BaseModel):
    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of user IDs to add to the conversation",
        examples=[["323e4567-e89b-12d3-a456-426614174002"]],
    )

    @field_validator("user_ids")
    @classmethod
    def deduplicate_user_ids(cls, v: list[UUID]) -> list[UUID]:
        """Remove duplicate user IDs while preserving order."""
        seen: set[UUID] = set()
        return [uid for uid in v if not (uid in seen or seen.add(uid))]  # type: ignore[func-returns-value]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_ids": [
                    "323e4567-e89b-12d3-a456-426614174002",
                    "423e4567-e89b-12d3-a456-426614174003",
                ]
            }
        }
    )
