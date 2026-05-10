import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.server_channel import ServerChannel


class ServerChannelMessage(Base, TimestampMixin):
    __tablename__ = "server_channel_messages"
    __table_args__ = (
        Index(
            "ix_server_channel_messages_channel_id_created_at_id",
            "channel_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_server_channel_messages_thread_root_message_id_created_at",
            "thread_root_message_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_root_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("server_channel_messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    channel: Mapped["ServerChannel"] = relationship()
