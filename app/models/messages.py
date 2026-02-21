import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IsDeletedMixin, TimestampMixin


class Message(Base, TimestampMixin, IsDeletedMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
        Index("idx_messages_sender", "sender_id"),
        Index("idx_messages_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_type: Mapped[str] = mapped_column(
        String(50), default="text", nullable=False
    )  # text, image, video, audio, file, system
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_edited: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    delivered_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversation = relationship("Conversation", back_populates="messages")
