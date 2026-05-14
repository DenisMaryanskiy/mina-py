from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReactionCreate(BaseModel):
    emoji: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Emoji character(s) to react with",
        examples=["👍"],
    )

    model_config = ConfigDict(json_schema_extra={"example": {"emoji": "👍"}})


class ReactionResponse(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the reaction")
    message_id: UUID = Field(
        ..., description="ID of the message that was reacted to"
    )
    user_id: UUID = Field(..., description="ID of the user who reacted")
    emoji: str = Field(..., description="Emoji used in the reaction")
    created_at: datetime = Field(
        ..., description="Timestamp when the reaction was added"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "823e4567-e89b-12d3-a456-426614174010",
                "message_id": "523e4567-e89b-12d3-a456-426614174004",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "emoji": "👍",
                "created_at": "2026-03-25T10:00:00Z",
            }
        },
    )


class ReactionSummaryItem(BaseModel):
    emoji: str = Field(..., description="The emoji character(s)")
    count: int = Field(
        ..., description="Number of users who reacted with this emoji"
    )
    user_ids: list[UUID] = Field(
        ..., description="IDs of users who reacted with this emoji"
    )


class ReactionSummaryResponse(BaseModel):
    message_id: UUID = Field(..., description="ID of the message")
    reactions: list[ReactionSummaryItem] = Field(
        default_factory=list,
        description="Reactions grouped by emoji with counts",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "523e4567-e89b-12d3-a456-426614174004",
                "reactions": [
                    {
                        "emoji": "👍",
                        "count": 3,
                        "user_ids": [
                            "123e4567-e89b-12d3-a456-426614174000",
                            "223e4567-e89b-12d3-a456-426614174001",
                        ],
                    }
                ],
            }
        }
    )
