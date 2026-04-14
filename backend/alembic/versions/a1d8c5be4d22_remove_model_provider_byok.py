"""remove model provider byok

Revision ID: a1d8c5be4d22
Revises: c91c6d7b2a1f
Create Date: 2026-04-08 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1d8c5be4d22"
down_revision: Union[str, Sequence[str], None] = "c91c6d7b2a1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RESERVED_USER_ENV_VAR_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "GLM_API_KEY",
    "GLM_BASE_URL",
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "SKILLSMP_API_KEY",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "user_env_vars" in table_names:
        user_env_vars = sa.table(
            "user_env_vars",
            sa.column("scope", sa.String(length=50)),
            sa.column("key", sa.String(length=255)),
        )
        op.execute(
            sa.delete(user_env_vars).where(
                user_env_vars.c.scope == "user",
                user_env_vars.c.key.in_(_RESERVED_USER_ENV_VAR_KEYS),
            )
        )

    if "user_model_provider_settings" in table_names:
        index_names = {
            index.get("name")
            for index in inspector.get_indexes("user_model_provider_settings")
        }
        if "ix_user_model_provider_settings_user_id" in index_names:
            op.drop_index(
                "ix_user_model_provider_settings_user_id",
                table_name="user_model_provider_settings",
            )
        op.drop_table("user_model_provider_settings")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "user_model_provider_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("model_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "provider_id",
            name="uq_user_model_provider_settings_user_provider",
        ),
    )
    op.create_index(
        "ix_user_model_provider_settings_user_id",
        "user_model_provider_settings",
        ["user_id"],
        unique=False,
    )
