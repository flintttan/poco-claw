"""add agent runtime binding

Revision ID: 8fd0f1d4f6c2
Revises: 73af4f9e2b31
Create Date: 2026-05-05 01:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8fd0f1d4f6c2"
down_revision: Union[str, Sequence[str], None] = "73af4f9e2b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_assignments",
        sa.Column("server_channel_task_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "agent_assignments",
        sa.Column("agent_identity_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_agent_assignments_server_channel_task_id"),
        "agent_assignments",
        ["server_channel_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_assignments_agent_identity_id"),
        "agent_assignments",
        ["agent_identity_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_agent_assignments_server_channel_task_id",
        "agent_assignments",
        "server_channel_tasks",
        ["server_channel_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_agent_assignments_agent_identity_id",
        "agent_assignments",
        "agent_identities",
        ["agent_identity_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_assignments_agent_identity_id",
        "agent_assignments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_agent_assignments_server_channel_task_id",
        "agent_assignments",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_agent_assignments_agent_identity_id"),
        table_name="agent_assignments",
    )
    op.drop_index(
        op.f("ix_agent_assignments_server_channel_task_id"),
        table_name="agent_assignments",
    )
    op.drop_column("agent_assignments", "agent_identity_id")
    op.drop_column("agent_assignments", "server_channel_task_id")
