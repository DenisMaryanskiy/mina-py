from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MESSAGE_TYPES = Literal["text", "image", "video", "audio", "file", "system"]


class MessageCreate(BaseModel):
    content: str | None = Field(
        None,
        min_length=1,
        max_length=10_000,
        description=(
            "Text content of the message. Required when message_type is 'text'."
        ),
        examples=["Hello there!"],
    )
    message_type: MESSAGE_TYPES = Field(
        default="text",
        description=(
            "Type of message content: text, image, video, audio, file, or system"
        ),
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description=(
            "Rich content metadata for non-text messages "
            "(e.g. file name, size, dimensions, duration)"
        ),
        examples=[{"file_name": "report.pdf", "file_size": 204800}],
    )
    reply_to_message_id: UUID | None = Field(
        None,
        description="ID of the message being replied to",
        examples=["523e4567-e89b-12d3-a456-426614174004"],
    )

    @model_validator(mode="after")
    def text_message_requires_content(self) -> "MessageCreate":
        """
        Text messages must have content.
        Other types carry their data in metadata.
        """
        if self.message_type == "text" and not self.content:
            raise ValueError("Text messages must have content.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Hello there!",
                "message_type": "text",
                "metadata": None,
                "reply_to_message_id": None,
            }
        }
    )


class MessageEdit(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Updated text content of the message",
        examples=["Corrected message content"],
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"content": "Corrected message content"}}
    )


class MessageResponse(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the message")
    conversation_id: UUID = Field(
        ..., description="Conversation this message belongs to"
    )
    sender_id: UUID = Field(..., description="User ID of the message sender")
    content: str | None = Field(None, description="Text content of the message")
    message_type: str = Field(..., description="Type of message content")
    metadata: dict[str, Any] | None = Field(
        None,
        alias="metadata_",
        description="Rich content metadata for non-text messages",
    )
    reply_to_message_id: UUID | None = Field(
        None, description="ID of the message this is a reply to"
    )
    is_edited: bool = Field(
        ..., description="Whether the message has been edited"
    )
    is_deleted: bool = Field(
        ..., description="Whether the message has been soft-deleted"
    )
    delivered_at: datetime | None = Field(
        None, description="Timestamp when the message was delivered"
    )
    read_at: datetime | None = Field(
        None, description="Timestamp when the message was first read"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the message was sent"
    )
    updated_at: datetime = Field(..., description="Timestamp of the last update")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "523e4567-e89b-12d3-a456-426614174004",
                "conversation_id": "223e4567-e89b-12d3-a456-426614174001",
                "sender_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Hello there!",
                "message_type": "text",
                "metadata": None,
                "reply_to_message_id": None,
                "is_edited": False,
                "is_deleted": False,
                "delivered_at": "2026-02-01T11:30:00Z",
                "read_at": None,
                "created_at": "2026-02-01T11:30:00Z",
                "updated_at": "2026-02-01T11:30:00Z",
            }
        },
    )


class PaginatedMessages(BaseModel):
    items: list[MessageResponse] = Field(
        ..., description="List of messages for the current page"
    )
    total: int = Field(
        ..., description="Total number of messages matching the query"
    )
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 42,
                "page": 1,
                "page_size": 50,
                "has_next": False,
                "has_prev": False,
            }
        }
    )


class MessageSearchResponse(BaseModel):
    items: list[MessageResponse] = Field(
        ..., description="Messages matching the search query"
    )
    total: int = Field(..., description="Total number of matching messages")
    query: str = Field(..., description="The search query that was executed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"items": [], "total": 3, "query": "hello"}
        }
    )
