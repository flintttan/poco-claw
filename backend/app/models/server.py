import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.server_channel import ServerChannel
    from app.models.server_invite import ServerInvite
    from app.models.server_member import ServerMember


class Server(Base, TimestampMixin):
    __tablename__ = "servers"
    __table_args__ = (UniqueConstraint("slug", name="uq_servers_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    members: Mapped[list["ServerMember"]] = relationship(
        back_populates="server",
        cascade="all, delete-orphan",
    )
    invites: Mapped[list["ServerInvite"]] = relationship(
        back_populates="server",
        cascade="all, delete-orphan",
    )
    channels: Mapped[list["ServerChannel"]] = relationship(
        back_populates="server",
        cascade="all, delete-orphan",
    )
