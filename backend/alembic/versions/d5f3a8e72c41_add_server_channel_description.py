"""add server channel description

Revision ID: d5f3a8e72c41
Revises: c0a0c1dd35a1
Create Date: 2026-05-05 17:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f3a8e72c41"
down_revision: Union[str, Sequence[str], None] = "c0a0c1dd35a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "server_channels",
        sa.Column("description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("server_channels", "description")
