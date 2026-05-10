"""add channel artifacts

Revision ID: 1c123413ec15
Revises: a8c4e9f1b2d3
Create Date: 2026-05-06 00:27:28.910826

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c123413ec15"
down_revision: Union[str, Sequence[str], None] = "a8c4e9f1b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "channel_artifacts",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("source_session_id", sa.Uuid(), nullable=False),
        sa.Column("agent_identity_id", sa.Uuid(), nullable=True),
        sa.Column("publisher_user_id", sa.String(length=255), nullable=True),
        sa.Column(
            "source_kind",
            sa.String(length=50),
            server_default=sa.text("'workspace_export'"),
            nullable=False,
        ),
        sa.Column("logical_path", sa.String(length=1024), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "is_previewable",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["agent_identity_id"], ["agent_identities.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["server_channels.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["publisher_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_session_id",
            "logical_path",
            name="uq_channel_artifacts_session_logical_path",
        ),
    )
    op.create_index(
        op.f("ix_channel_artifacts_agent_identity_id"),
        "channel_artifacts",
        ["agent_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_artifacts_channel_id"),
        "channel_artifacts",
        ["channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_artifacts_publisher_user_id"),
        "channel_artifacts",
        ["publisher_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_artifacts_server_id"),
        "channel_artifacts",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_artifacts_source_session_id"),
        "channel_artifacts",
        ["source_session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_channel_artifacts_source_session_id"), table_name="channel_artifacts"
    )
    op.drop_index(
        op.f("ix_channel_artifacts_server_id"), table_name="channel_artifacts"
    )
    op.drop_index(
        op.f("ix_channel_artifacts_publisher_user_id"), table_name="channel_artifacts"
    )
    op.drop_index(
        op.f("ix_channel_artifacts_channel_id"), table_name="channel_artifacts"
    )
    op.drop_index(
        op.f("ix_channel_artifacts_agent_identity_id"), table_name="channel_artifacts"
    )
    op.drop_table("channel_artifacts")
