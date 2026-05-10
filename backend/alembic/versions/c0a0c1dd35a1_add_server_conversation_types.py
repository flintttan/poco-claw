"""add server conversation types

Revision ID: c0a0c1dd35a1
Revises: 8fd0f1d4f6c2
Create Date: 2026-05-05 01:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0a0c1dd35a1"
down_revision: Union[str, Sequence[str], None] = "8fd0f1d4f6c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "server_channels",
        sa.Column(
            "conversation_type",
            sa.String(length=50),
            server_default=sa.text("'channel'"),
            nullable=False,
        ),
    )
    op.add_column(
        "server_channels",
        sa.Column("direct_user_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "server_channels",
        sa.Column("direct_agent_identity_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_server_channels_conversation_type"),
        "server_channels",
        ["conversation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channels_direct_user_id"),
        "server_channels",
        ["direct_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channels_direct_agent_identity_id"),
        "server_channels",
        ["direct_agent_identity_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_server_channels_direct_user_id",
        "server_channels",
        "users",
        ["direct_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_server_channels_direct_agent_identity_id",
        "server_channels",
        "agent_identities",
        ["direct_agent_identity_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_server_channels_direct_agent_identity_id",
        "server_channels",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_server_channels_direct_user_id",
        "server_channels",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_server_channels_direct_agent_identity_id"),
        table_name="server_channels",
    )
    op.drop_index(
        op.f("ix_server_channels_direct_user_id"),
        table_name="server_channels",
    )
    op.drop_index(
        op.f("ix_server_channels_conversation_type"),
        table_name="server_channels",
    )
    op.drop_column("server_channels", "direct_agent_identity_id")
    op.drop_column("server_channels", "direct_user_id")
    op.drop_column("server_channels", "conversation_type")
