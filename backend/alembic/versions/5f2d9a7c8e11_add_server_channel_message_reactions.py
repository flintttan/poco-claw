"""add server channel message reactions

Revision ID: 5f2d9a7c8e11
Revises: 1c123413ec15
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f2d9a7c8e11"
down_revision: Union[str, Sequence[str], None] = "1c123413ec15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "server_channel_message_reactions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.UUID(), nullable=False),
        sa.Column("emoji", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", sa.String(length=255), nullable=True),
        sa.Column("actor_agent_identity_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint(
            "actor_type in ('user', 'agent')",
            name="ck_server_channel_message_reactions_actor_type",
        ),
        sa.CheckConstraint(
            (
                "(actor_type = 'user' and actor_user_id is not null "
                "and actor_agent_identity_id is null) or "
                "(actor_type = 'agent' and actor_agent_identity_id is not null "
                "and actor_user_id is null)"
            ),
            name="ck_server_channel_message_reactions_actor_identity",
        ),
        sa.ForeignKeyConstraint(
            ["actor_agent_identity_id"],
            ["agent_identities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["server_channels.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["server_channel_messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_server_channel_message_reactions_actor_agent_identity_id"),
        "server_channel_message_reactions",
        ["actor_agent_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_message_reactions_actor_user_id"),
        "server_channel_message_reactions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_message_reactions_channel_id"),
        "server_channel_message_reactions",
        ["channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_message_reactions_message_id"),
        "server_channel_message_reactions",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "uq_server_channel_message_reactions_agent_actor",
        "server_channel_message_reactions",
        ["message_id", "emoji", "actor_agent_identity_id"],
        unique=True,
        postgresql_where=sa.text("actor_type = 'agent'"),
    )
    op.create_index(
        "uq_server_channel_message_reactions_user_actor",
        "server_channel_message_reactions",
        ["message_id", "emoji", "actor_user_id"],
        unique=True,
        postgresql_where=sa.text("actor_type = 'user'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_server_channel_message_reactions_user_actor",
        table_name="server_channel_message_reactions",
        postgresql_where=sa.text("actor_type = 'user'"),
    )
    op.drop_index(
        "uq_server_channel_message_reactions_agent_actor",
        table_name="server_channel_message_reactions",
        postgresql_where=sa.text("actor_type = 'agent'"),
    )
    op.drop_index(
        op.f("ix_server_channel_message_reactions_message_id"),
        table_name="server_channel_message_reactions",
    )
    op.drop_index(
        op.f("ix_server_channel_message_reactions_channel_id"),
        table_name="server_channel_message_reactions",
    )
    op.drop_index(
        op.f("ix_server_channel_message_reactions_actor_user_id"),
        table_name="server_channel_message_reactions",
    )
    op.drop_index(
        op.f("ix_server_channel_message_reactions_actor_agent_identity_id"),
        table_name="server_channel_message_reactions",
    )
    op.drop_table("server_channel_message_reactions")
