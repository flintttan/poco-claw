"""add channel owner and server binding

Revision ID: 2b9d4e7c3a1f
Revises: 2a7f3c1d4e8b
Create Date: 2026-06-24 12:30:00.000000

"""

import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2b9d4e7c3a1f"
down_revision: Union[str, Sequence[str], None] = "2b7e4c91d6a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default user id used to backfill owner_user_id for legacy channels.
# This mirrors settings.backend_user_id; if that env var is set, use it.
_LEGACY_OWNER_ID = (os.environ.get("BACKEND_USER_ID") or "default").strip() or "default"


def upgrade() -> None:
    """Add owner_user_id, server binding, and chat_type to channels.

    Existing rows are backfilled with the legacy BACKEND_USER_ID so that
    historical IM traffic continues to flow without manual intervention.
    """
    bind = op.get_bind()

    # Ensure a legacy owner user exists in users (FK target).
    bind.execute(
        sa.text(
            """
            INSERT INTO users (id, status, system_role, created_at, updated_at)
            VALUES (:uid, 'active', 'user', now(), now())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"uid": _LEGACY_OWNER_ID},
    )

    op.add_column(
        "channels",
        sa.Column(
            "chat_type",
            sa.String(length=16),
            server_default=sa.text("'group'"),
            nullable=False,
        ),
    )
    op.add_column(
        "channels",
        sa.Column(
            "owner_user_id",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text(f"'{_LEGACY_OWNER_ID}'"),
        ),
    )
    op.add_column(
        "channels",
        sa.Column("server_id", postgresql.UUID(), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column(
            "server_channel_id",
            postgresql.UUID(),
            nullable=True,
        ),
    )
    op.add_column(
        "channels",
        sa.Column("last_bound_by_user_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column("last_bound_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        op.f("ix_channels_owner_user_id"),
        "channels",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channels_server_id"),
        "channels",
        ["server_id"],
        unique=False,
    )

    # Backfill: all existing channels get the legacy owner.
    bind.execute(
        sa.text(
            "UPDATE channels SET owner_user_id = :uid WHERE owner_user_id IS NULL OR owner_user_id = ''"
        ),
        {"uid": _LEGACY_OWNER_ID},
    )

    # Drop the server default now that all rows have a real value.
    op.alter_column("channels", "owner_user_id", server_default=None)

    op.create_foreign_key(
        "fk_channels_owner_user_id",
        "channels",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_channels_server_id",
        "channels",
        "servers",
        ["server_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_channels_server_channel_id",
        "channels",
        "server_channels",
        ["server_channel_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_channels_last_bound_by_user_id",
        "channels",
        "users",
        ["last_bound_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove owner_user_id, server binding, and chat_type from channels."""
    op.drop_constraint(
        "fk_channels_last_bound_by_user_id", "channels", type_="foreignkey"
    )
    op.drop_constraint("fk_channels_server_channel_id", "channels", type_="foreignkey")
    op.drop_constraint("fk_channels_server_id", "channels", type_="foreignkey")
    op.drop_constraint("fk_channels_owner_user_id", "channels", type_="foreignkey")
    op.drop_index(op.f("ix_channels_server_id"), table_name="channels")
    op.drop_index(op.f("ix_channels_owner_user_id"), table_name="channels")
    op.drop_column("channels", "last_bound_at")
    op.drop_column("channels", "last_bound_by_user_id")
    op.drop_column("channels", "server_channel_id")
    op.drop_column("channels", "server_id")
    op.drop_column("channels", "owner_user_id")
    op.drop_column("channels", "chat_type")
