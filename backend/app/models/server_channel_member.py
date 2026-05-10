import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.server_channel import ServerChannel


class ServerChannelMember(Base, TimestampMixin):
    __tablename__ = "server_channel_members"
    __table_args__ = (
        UniqueConstraint(
            "channel_id",
            "user_id",
            name="uq_server_channel_members_channel_id_user_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    channel: Mapped["ServerChannel"] = relationship(back_populates="members")
