"""add server channel tasks

Revision ID: 5dabd02f9e77
Revises: 90878d18dc71
Create Date: 2026-05-04 22:32:51.358227

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5dabd02f9e77"
down_revision: Union[str, Sequence[str], None] = "90878d18dc71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "server_channel_tasks",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'todo'"),
            nullable=False,
        ),
        sa.Column(
            "position", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee_user_id", sa.String(length=255), nullable=True),
        sa.Column("assignee_preset_id", sa.Integer(), nullable=True),
        sa.Column("reporter_user_id", sa.String(length=255), nullable=True),
        sa.Column("related_project_id", sa.Uuid(), nullable=True),
        sa.Column("creator_user_id", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("thread_root_message_id", sa.Uuid(), nullable=True),
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
            ["assignee_preset_id"], ["presets.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["server_channels.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["related_project_id"], ["projects.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["thread_root_message_id"],
            ["server_channel_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_root_message_id",
            name="uq_server_channel_tasks_thread_root_message_id",
        ),
    )
    op.create_index(
        op.f("ix_server_channel_tasks_assignee_preset_id"),
        "server_channel_tasks",
        ["assignee_preset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_assignee_user_id"),
        "server_channel_tasks",
        ["assignee_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_channel_id"),
        "server_channel_tasks",
        ["channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_creator_user_id"),
        "server_channel_tasks",
        ["creator_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_priority"),
        "server_channel_tasks",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_related_project_id"),
        "server_channel_tasks",
        ["related_project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_server_id"),
        "server_channel_tasks",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_status"),
        "server_channel_tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_thread_root_message_id"),
        "server_channel_tasks",
        ["thread_root_message_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_server_channel_tasks_thread_root_message_id"),
        table_name="server_channel_tasks",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_status"), table_name="server_channel_tasks"
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_server_id"), table_name="server_channel_tasks"
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_related_project_id"),
        table_name="server_channel_tasks",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_priority"), table_name="server_channel_tasks"
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_creator_user_id"),
        table_name="server_channel_tasks",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_channel_id"), table_name="server_channel_tasks"
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_assignee_user_id"),
        table_name="server_channel_tasks",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_assignee_preset_id"),
        table_name="server_channel_tasks",
    )
    op.drop_table("server_channel_tasks")
