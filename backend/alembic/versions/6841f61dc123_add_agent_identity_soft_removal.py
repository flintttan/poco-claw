"""add agent identity soft removal

Revision ID: 6841f61dc123
Revises: 5f2d9a7c8e11
Create Date: 2026-05-08 22:50:05.299972

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6841f61dc123"
down_revision: Union[str, Sequence[str], None] = "5f2d9a7c8e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_identities",
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_identities",
        sa.Column("removed_by", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_agent_identities_removed_at"),
        "agent_identities",
        ["removed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_identities_removed_at"), table_name="agent_identities")
    op.drop_column("agent_identities", "removed_by")
    op.drop_column("agent_identities", "removed_at")
