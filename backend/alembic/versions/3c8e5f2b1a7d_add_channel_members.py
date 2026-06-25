"""add channel members

Revision ID: 3c8e5f2b1a7d
Revises: 2b9d4e7c3a1f
Create Date: 2026-06-24 12:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c8e5f2b1a7d"
down_revision: Union[str, Sequence[str], None] = "2b9d4e7c3a1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create channel_members table for per-user ACL within IM channels.

    Each row represents a Poco user who is allowed to interact via a
    specific IM channel (Feishu chat, DingTalk conversation, Telegram
    chat, etc.). The role distinguishes the channel "anchor" (owner)
    from regular members.
    """
    op.create_table(
        "channel_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            server_default=sa.text("'member'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "user_id", name="uq_channel_member"),
    )
    op.create_index(
        op.f("ix_channel_members_channel_id"),
        "channel_members",
        ["channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_members_user_id"),
        "channel_members",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop channel_members table."""
    op.drop_index(op.f("ix_channel_members_user_id"), table_name="channel_members")
    op.drop_index(op.f("ix_channel_members_channel_id"), table_name="channel_members")
    op.drop_table("channel_members")
