"""add session cancellation state

Revision ID: c9d83ea69bc6
Revises: a1d8c5be4d22
Create Date: 2026-04-08 16:35:44.922899

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d83ea69bc6"
down_revision: Union[str, Sequence[str], None] = "a1d8c5be4d22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "agent_sessions",
        sa.Column(
            "cancellation_requested_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "agent_sessions",
        sa.Column(
            "cancellation_completed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("cancellation_target_run_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "agent_sessions",
        sa.Column(
            "cancellation_target_worker_id", sa.String(length=255), nullable=True
        ),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("cancellation_claimed_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent_sessions",
        sa.Column(
            "cancellation_lease_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("cancellation_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_agent_sessions_cancellation_requested_at"),
        "agent_sessions",
        ["cancellation_requested_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_sessions_cancellation_target_run_id"),
        "agent_sessions",
        ["cancellation_target_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_sessions_cancellation_target_worker_id"),
        "agent_sessions",
        ["cancellation_target_worker_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_sessions_cancellation_claimed_by"),
        "agent_sessions",
        ["cancellation_claimed_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_sessions_cancellation_lease_expires_at"),
        "agent_sessions",
        ["cancellation_lease_expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_sessions_status_cancel_target_requested",
        "agent_sessions",
        ["status", "cancellation_target_worker_id", "cancellation_requested_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_agent_sessions_status_cancel_target_requested",
        table_name="agent_sessions",
    )
    op.drop_index(
        op.f("ix_agent_sessions_cancellation_lease_expires_at"),
        table_name="agent_sessions",
    )
    op.drop_index(
        op.f("ix_agent_sessions_cancellation_claimed_by"),
        table_name="agent_sessions",
    )
    op.drop_index(
        op.f("ix_agent_sessions_cancellation_target_worker_id"),
        table_name="agent_sessions",
    )
    op.drop_index(
        op.f("ix_agent_sessions_cancellation_target_run_id"),
        table_name="agent_sessions",
    )
    op.drop_index(
        op.f("ix_agent_sessions_cancellation_requested_at"),
        table_name="agent_sessions",
    )
    op.drop_column("agent_sessions", "cancellation_error")
    op.drop_column("agent_sessions", "cancellation_lease_expires_at")
    op.drop_column("agent_sessions", "cancellation_claimed_by")
    op.drop_column("agent_sessions", "cancellation_reason")
    op.drop_column("agent_sessions", "cancellation_target_worker_id")
    op.drop_column("agent_sessions", "cancellation_target_run_id")
    op.drop_column("agent_sessions", "cancellation_completed_at")
    op.drop_column("agent_sessions", "cancellation_requested_at")
