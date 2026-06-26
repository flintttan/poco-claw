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

    Order matters:
    1. Ensure the legacy owner user exists in ``users`` (FK target). If it
       is missing, creating the FK in step 7 would fail.
    2. Pre-flight count of channels that will receive a non-null value, so
       the operator can see the migration scope before it runs.
    3. Add the new columns with a server_default — PostgreSQL backfills
       existing rows in a single rewrite, so the explicit UPDATE in step
       5 is a belt-and-braces fix for any rows that somehow miss it.
    4. Drop the server default, then add the FK constraint.
    5. Post-backfill verification: assert every row has an owner_user_id
       and that the legacy user was actually populated. Fail loudly if
       either condition is violated, so partial migrations cannot leave
       a NULL owner_user_id in production.
    """
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Pre-flight: ensure legacy owner exists (FK target).
    # ------------------------------------------------------------------
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
    # Defensive: confirm the user actually exists before we add a NOT NULL
    # column with an FK pointing at it. This catches the (rare) case where
    # ON CONFLICT silently dropped the insert — e.g. a trigger on users
    # that rejects the row, or a concurrent migration that just deleted
    # the legacy user.
    legacy_row = bind.execute(
        sa.text("SELECT id FROM users WHERE id = :uid"),
        {"uid": _LEGACY_OWNER_ID},
    ).first()
    if legacy_row is None:
        raise RuntimeError(
            f"migration backfill precheck failed: legacy owner user "
            f"{_LEGACY_OWNER_ID!r} is not present in users. "
            f"Create it manually before re-running this migration."
        )

    # ------------------------------------------------------------------
    # 2. Pre-flight: report the scope so operators can see the count.
    # ------------------------------------------------------------------
    preflight = bind.execute(sa.text("SELECT count(*) AS n FROM channels")).first()
    preflight_count = int(preflight.n) if preflight is not None else 0
    # Use a structured log line via print — Alembic captures stdout in
    # the migration log, so this surfaces in ``alembic upgrade`` output.
    print(
        f"[2b9d4e7c3a1f] backfill scope: {preflight_count} channels will "
        f"receive owner_user_id={_LEGACY_OWNER_ID!r}"
    )

    # ------------------------------------------------------------------
    # 3. Add columns. server_default backfills existing rows in-place.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 4. Belt-and-braces backfill: in case the server_default was
    # suppressed (e.g. a row was added concurrently between step 3 and
    # now, or a partial-failure state already has NULL owner_user_id).
    # ------------------------------------------------------------------
    bind.execute(
        sa.text(
            "UPDATE channels SET owner_user_id = :uid "
            "WHERE owner_user_id IS NULL OR owner_user_id = ''"
        ),
        {"uid": _LEGACY_OWNER_ID},
    )

    # ------------------------------------------------------------------
    # 5. Post-backfill verification: refuse to proceed if any row is
    # still NULL, otherwise the FK creation in step 7 will fail with
    # a less actionable error message.
    # ------------------------------------------------------------------
    null_check = bind.execute(
        sa.text(
            "SELECT count(*) AS n FROM channels WHERE owner_user_id IS NULL OR owner_user_id = ''"
        )
    ).first()
    null_count = int(null_check.n) if null_check is not None else 0
    if null_count > 0:
        raise RuntimeError(
            f"migration backfill verification failed: {null_count} "
            f"channels still have a NULL/empty owner_user_id after the "
            f"backfill UPDATE. Inspect the table and re-run."
        )

    # Drop the server default now that all rows have a real value.
    op.alter_column("channels", "owner_user_id", server_default=None)

    # ------------------------------------------------------------------
    # 6. Foreign keys.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 7. Done — print a final summary.
    # ------------------------------------------------------------------
    print(
        f"[2b9d4e7c3a1f] backfill complete: {preflight_count} channels "
        f"assigned to legacy owner {_LEGACY_OWNER_ID!r}"
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
