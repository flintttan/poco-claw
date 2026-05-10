import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class ServerChannelMessageReaction(Base, TimestampMixin):
    __tablename__ = "server_channel_message_reactions"
    __table_args__ = (
        CheckConstraint(
            "actor_type in ('user', 'agent')",
            name="ck_server_channel_message_reactions_actor_type",
        ),
        CheckConstraint(
            (
                "(actor_type = 'user' and actor_user_id is not null "
                "and actor_agent_identity_id is null) or "
                "(actor_type = 'agent' and actor_agent_identity_id is not null "
                "and actor_user_id is null)"
            ),
            name="ck_server_channel_message_reactions_actor_identity",
        ),
        Index(
            "uq_server_channel_message_reactions_user_actor",
            "message_id",
            "emoji",
            "actor_user_id",
            unique=True,
            postgresql_where=text("actor_type = 'user'"),
        ),
        Index(
            "uq_server_channel_message_reactions_agent_actor",
            "message_id",
            "emoji",
            "actor_agent_identity_id",
            unique=True,
            postgresql_where=text("actor_type = 'agent'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channel_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_agent_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
