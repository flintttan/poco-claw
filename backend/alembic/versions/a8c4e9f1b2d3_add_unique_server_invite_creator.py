"""add unique server invite creator

Revision ID: a8c4e9f1b2d3
Revises: d5f3a8e72c41
Create Date: 2026-05-05 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a8c4e9f1b2d3"
down_revision: Union[str, Sequence[str], None] = "d5f3a8e72c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM server_invites existing
        USING server_invites duplicate
        WHERE existing.server_id = duplicate.server_id
          AND existing.created_by = duplicate.created_by
          AND existing.created_at < duplicate.created_at
        """
    )
    op.create_unique_constraint(
        "uq_server_invites_server_id_created_by",
        "server_invites",
        ["server_id", "created_by"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_server_invites_server_id_created_by",
        "server_invites",
        type_="unique",
    )
