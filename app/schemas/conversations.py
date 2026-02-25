from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.participants import ParticipantResponse


class ConversationCreate(BaseModel):
    type: Literal["direct", "group"] = Field(
        ...,
        description=(
            "Conversation type: 'direct' for 1-on-1, 'group' for multi-user"
        ),
    )
    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description=(
            "Display name of the conversation. Required for group conversations."
        ),
        examples=["Project Alpha"],
    )
    avatar_url: str | None = Field(
        None,
        max_length=500,
        description="URL to the conversation avatar image",
        examples=["https://example.com/avatars/group.jpg"],
    )
    participant_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=50,
        description=(
            "User IDs to add as participants. "
            "For direct conversations, exactly one ID is required. "
            "Creator is always added automatically."
        ),
        examples=[["323e4567-e89b-12d3-a456-426614174002"]],
    )

    @field_validator("participant_ids")
    @classmethod
    def deduplicate_participant_ids(cls, v: list[UUID]) -> list[UUID]:
        """Remove duplicate participant IDs while preserving order."""
        seen: set[UUID] = set()
        return [uid for uid in v if not (uid in seen or seen.add(uid))]  # type: ignore[func-returns-value]

    @model_validator(mode="after")
    def validate_conversation_rules(self) -> "ConversationCreate":
        """Enforce type-specific rules that are knowable from input alone."""
        if self.type == "group" and not self.name:
            raise ValueError("Group conversations require a name.")
        if self.type == "direct" and len(self.participant_ids) != 1:
            raise ValueError(
                "Direct conversations require exactly one participant ID."
            )
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "direct",
                "participant_ids": ["323e4567-e89b-12d3-a456-426614174002"],
            }
        }
    )


class ConversationResponse(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the conversation")
    type: str = Field(..., description="Conversation type: 'direct' or 'group'")
    name: str | None = Field(
        None, description="Display name (group conversations only)"
    )
    avatar_url: str | None = Field(
        None, description="URL to the conversation avatar image"
    )
    created_by: UUID | None = Field(
        None, description="User ID of the conversation creator"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the conversation was created"
    )
    updated_at: datetime = Field(..., description="Timestamp of the last update")
    last_message_at: datetime | None = Field(
        None, description="Timestamp of the most recent message"
    )
    participants: list[ParticipantResponse] = Field(
        default_factory=list, description="List of conversation participants"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "type": "direct",
                "name": None,
                "avatar_url": None,
                "created_by": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2026-02-01T10:00:00Z",
                "updated_at": "2026-02-01T10:00:00Z",
                "last_message_at": "2026-02-01T11:30:00Z",
                "participants": [],
            }
        },
    )


class ConversationListItem(BaseModel):
    """Lightweight conversation summary for list views."""

    id: UUID = Field(..., description="Unique identifier of the conversation")
    type: str = Field(..., description="Conversation type: 'direct' or 'group'")
    name: str | None = Field(
        None, description="Display name (group conversations only)"
    )
    avatar_url: str | None = Field(
        None, description="URL to the conversation avatar image"
    )
    created_by: UUID | None = Field(
        None, description="User ID of the conversation creator"
    )
    last_message_at: datetime | None = Field(
        None, description="Timestamp of the most recent message"
    )
    participant_count: int = Field(
        default=0, description="Total number of participants in the conversation"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "type": "group",
                "name": "Project Alpha",
                "avatar_url": "https://example.com/avatars/group.jpg",
                "created_by": "123e4567-e89b-12d3-a456-426614174000",
                "last_message_at": "2026-02-01T11:30:00Z",
                "participant_count": 5,
            }
        },
    )
