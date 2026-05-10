import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class ServerChannelAgentMember(Base, TimestampMixin):
    __tablename__ = "server_channel_agent_members"
    __table_args__ = (
        UniqueConstraint(
            "channel_id",
            "agent_identity_id",
            name="uq_server_channel_agent_members_channel_agent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="CASCADE"),
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
