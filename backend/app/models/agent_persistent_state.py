import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_identity import AgentIdentity


class AgentPersistentState(Base, TimestampMixin):
    __tablename__ = "agent_persistent_states"
    __table_args__ = (
        UniqueConstraint(
            "agent_identity_id",
            name="uq_agent_persistent_states_agent_identity_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state_root_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    profile_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    memory_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    notes_dir_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    state_dir_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifacts_dir_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    state_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    runtime_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="idle",
        server_default=text("'idle'"),
        index=True,
    )
    active_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("server_channel_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    active_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_written_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    agent_identity: Mapped["AgentIdentity"] = relationship(
        back_populates="persistent_state"
    )
