import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MessageAttachment(Base, TimestampMixin):
    __tablename__ = "message_attachments"
    __table_args__ = (Index("idx_attachments_message", "message_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # image, video, audio, document

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)

    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    duration: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # seconds, for audio/video
    dimensions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"width": 1920, "height": 1080}
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    message = relationship("Message", back_populates="attachments")
