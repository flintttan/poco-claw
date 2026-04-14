"""clear unverified primary emails

Revision ID: c91c6d7b2a1f
Revises: b0d7d7f5f351
Create Date: 2026-04-08 10:15:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c91c6d7b2a1f"
down_revision: Union[str, Sequence[str], None] = "b0d7d7f5f351"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clear primary emails that are not backed by a verified identity."""
    op.execute(
        """
        UPDATE users
        SET primary_email = NULL,
            updated_at = now()
        WHERE primary_email IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM auth_identities
              WHERE auth_identities.user_id = users.id
                AND auth_identities.email_verified IS TRUE
                AND auth_identities.provider_email = users.primary_email
          )
        """
    )


def downgrade() -> None:
    """Downgrade is irreversible because cleared emails cannot be recovered."""
    pass
