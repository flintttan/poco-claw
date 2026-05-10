import uuid
from datetime import datetime
import re
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_persistent_state import AgentPersistentState


class AgentIdentity(Base, TimestampMixin):
    __tablename__ = "agent_identities"
    __table_args__ = (
        UniqueConstraint(
            "server_id", "handle", name="uq_agent_identities_server_handle"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preset_id: Mapped[int] = mapped_column(
        ForeignKey("presets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handle: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_key: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="server",
        server_default=text("'server'"),
    )
    lifecycle_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    removed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    persistent_state: Mapped["AgentPersistentState | None"] = relationship(
        back_populates="agent_identity",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @staticmethod
    def slugify_handle(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "agent"
