import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("provider", "destination", name="uq_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    # Per-user semantics: when True, this channel receives events only for
    # sessions whose owner_user_id matches its own owner_user_id.
    subscribe_all: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    # "p2p" (1:1 with the bot) or "group" (multi-user chat).
    chat_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'group'"),
    )
    # Poco user who "owns" this IM chat's binding. For p2p, the chatting
    # user. For groups, the first user to interact (anchor for /bind).
    owner_user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Optional binding to a Poco server (workspace) - enables multi-user
    # shared sessions within the IM chat.
    server_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Optional binding to a specific channel within the bound server.
    server_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("server_channels.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Audit fields for the most recent /bind.
    last_bound_by_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_bound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    members: Mapped[list["ChannelMember"]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
    )


class ChannelMember(Base, TimestampMixin):
    """Per-user ACL for an IM channel.

    Any Poco user who interacts with an IM channel is auto-registered as a
    member. The ``role`` distinguishes the channel "anchor" (``owner``,
    typically the first user or the user who ran ``/bind``) from regular
    participants (``member``). Used for outbound event fan-out ACL and
    shared-session access checks.
    """

    __tablename__ = "channel_members"
    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_channel_member"),
        Index("ix_channel_members_user_id", "user_id", "channel_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # "owner" (channel anchor) | "member"
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="member",
        server_default=text("'member'"),
    )
    # "active" | "removed"
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    channel: Mapped["Channel"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class ChannelDelivery(Base, TimestampMixin):
    __tablename__ = "channel_deliveries"
    __table_args__ = (
        UniqueConstraint("channel_id", name="uq_channel_delivery_channel_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    send_address: Mapped[str] = mapped_column(String(2048), nullable=False)


class ActiveSession(Base, TimestampMixin):
    __tablename__ = "active_sessions"
    __table_args__ = (UniqueConstraint("channel_id", name="uq_active_session_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class WatchedSession(Base, TimestampMixin):
    __tablename__ = "watched_sessions"
    __table_args__ = (
        UniqueConstraint("channel_id", "session_id", name="uq_watch_channel_session"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class ImBinding(Base, TimestampMixin):
    """Provider-agnostic link between a Poco user and an IM identity.

    A Poco user can be bound to many IM identities across many
    providers (one per Feishu account, one per DingTalk account, etc.),
    and conversely an IM identity can be bound to at most one Poco user
    (enforced by the ``(provider, im_user_id)`` UNIQUE constraint).

    ``bound_via`` records the binding origin so the UI can show a
    different message for OAuth-auto bindings vs. code-based ones:
      - ``code``: the user generated a code in the web UI and typed
        it in the IM chat.
      - ``oauth_auto``: a Feishu/DingTalk OAuth login also created an
        IM binding automatically.
      - ``admin``: an operator linked the accounts out-of-band.
    """

    __tablename__ = "im_bindings"
    __table_args__ = (
        UniqueConstraint(
            "provider", "im_user_id", name="uq_im_bindings_provider_im_user_id"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # Feishu open_id / DingTalk staffId / Telegram user.id, etc.
    im_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional cross-app identity (e.g. Feishu union_id, DingTalk
    # unionId). Indexed via the composite index below to allow
    # lookups from IM events that carry only the union id.
    im_union_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    im_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bound_via: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="code",
        server_default=text("'code'"),
    )
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship()


class ImBindingCode(Base):
    """Short-lived, single-use code bridging web OAuth to IM linking.

    The web UI calls ``POST /me/binding-codes`` to mint a code bound to
    the calling user. The user then sends ``bind <code>`` in any IM
    chat the bot is in. The inbound service consumes the code to
    create an ``ImBinding`` between that user and the IM identity that
    sent the message.

    Codes are 8-character Crockford base32 strings (≈32^8 entropy),
    expire 10 minutes after creation, and are consumed once. The
    table has no TimestampMixin because the relevant timestamps
    (created_at, expires_at, consumed_at) are first-class fields.
    """

    __tablename__ = "im_binding_codes"
    __table_args__ = (UniqueConstraint("code", name="uq_im_binding_codes_code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Optional pre-fill: when the web UI requests a code for a specific
    # provider, only messages from that provider will accept it. ``None``
    # means the code is accepted from any provider the user wants to
    # bind (e.g. they generated a generic "bind something" code).
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Audit: which IM identity consumed this code.
    consumed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship()


class DedupEvent(Base):
    __tablename__ = "dedup_events"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ImEventOutbox(Base, TimestampMixin):
    __tablename__ = "im_event_outbox"
    __table_args__ = (
        Index(
            "ix_im_event_outbox_status_next_attempt_at_created_at",
            "status",
            "next_attempt_at",
            "created_at",
        ),
        Index("ix_im_event_outbox_session_id", "session_id"),
        Index("ix_im_event_outbox_run_id", "run_id"),
        Index("ix_im_event_outbox_user_input_request_id", "user_input_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_input_request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
