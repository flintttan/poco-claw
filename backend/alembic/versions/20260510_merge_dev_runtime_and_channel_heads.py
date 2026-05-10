"""merge dev runtime policy and channel collaboration heads

Revision ID: 20260510_merge_heads
Revises: (20260430_runtime_env_policy, 6841f61dc123)
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence


revision: str = "20260510_merge_heads"
down_revision: str | Sequence[str] | None = (
    "20260430_runtime_env_policy",
    "6841f61dc123",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
