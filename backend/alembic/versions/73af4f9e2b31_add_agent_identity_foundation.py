"""add agent identity foundation

Revision ID: 73af4f9e2b31
Revises: 5dabd02f9e77
Create Date: 2026-05-05 00:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "73af4f9e2b31"
down_revision: Union[str, Sequence[str], None] = "5dabd02f9e77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_identities",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("preset_id", sa.Integer(), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visual_key", sa.String(length=100), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=50),
            server_default=sa.text("'server'"),
            nullable=False,
        ),
        sa.Column(
            "lifecycle_state",
            sa.String(length=50),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["preset_id"], ["presets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_id", "handle", name="uq_agent_identities_server_handle"
        ),
    )
    op.create_index(
        op.f("ix_agent_identities_server_id"),
        "agent_identities",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identities_preset_id"),
        "agent_identities",
        ["preset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identities_handle"), "agent_identities", ["handle"], unique=False
    )
    op.create_index(
        op.f("ix_agent_identities_lifecycle_state"),
        "agent_identities",
        ["lifecycle_state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identities_created_by"),
        "agent_identities",
        ["created_by"],
        unique=False,
    )

    op.create_table(
        "agent_persistent_states",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("agent_identity_id", sa.Uuid(), nullable=False),
        sa.Column("state_root_path", sa.String(length=1024), nullable=False),
        sa.Column("profile_path", sa.String(length=1024), nullable=False),
        sa.Column("memory_path", sa.String(length=1024), nullable=False),
        sa.Column("notes_dir_path", sa.String(length=1024), nullable=False),
        sa.Column("state_dir_path", sa.String(length=1024), nullable=False),
        sa.Column("artifacts_dir_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "state_version", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "runtime_status",
            sa.String(length=50),
            server_default=sa.text("'idle'"),
            nullable=False,
        ),
        sa.Column("active_task_id", sa.Uuid(), nullable=True),
        sa.Column("active_session_id", sa.Uuid(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_written_at", sa.DateTime(timezone=True), nullable=True),
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
            ["active_session_id"], ["agent_sessions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["active_task_id"], ["server_channel_tasks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["agent_identity_id"], ["agent_identities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_identity_id",
            name="uq_agent_persistent_states_agent_identity_id",
        ),
    )
    op.create_index(
        op.f("ix_agent_persistent_states_agent_identity_id"),
        "agent_persistent_states",
        ["agent_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_persistent_states_runtime_status"),
        "agent_persistent_states",
        ["runtime_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_persistent_states_active_task_id"),
        "agent_persistent_states",
        ["active_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_persistent_states_active_session_id"),
        "agent_persistent_states",
        ["active_session_id"],
        unique=False,
    )

    op.create_table(
        "server_channel_agent_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("agent_identity_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
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
            ["agent_identity_id"], ["agent_identities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["server_channels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel_id",
            "agent_identity_id",
            name="uq_server_channel_agent_members_channel_agent",
        ),
    )
    op.create_index(
        op.f("ix_server_channel_agent_members_channel_id"),
        "server_channel_agent_members",
        ["channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_agent_members_agent_identity_id"),
        "server_channel_agent_members",
        ["agent_identity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_server_channel_agent_members_agent_identity_id"),
        table_name="server_channel_agent_members",
    )
    op.drop_index(
        op.f("ix_server_channel_agent_members_channel_id"),
        table_name="server_channel_agent_members",
    )
    op.drop_table("server_channel_agent_members")

    op.drop_index(
        op.f("ix_agent_persistent_states_active_session_id"),
        table_name="agent_persistent_states",
    )
    op.drop_index(
        op.f("ix_agent_persistent_states_active_task_id"),
        table_name="agent_persistent_states",
    )
    op.drop_index(
        op.f("ix_agent_persistent_states_runtime_status"),
        table_name="agent_persistent_states",
    )
    op.drop_index(
        op.f("ix_agent_persistent_states_agent_identity_id"),
        table_name="agent_persistent_states",
    )
    op.drop_table("agent_persistent_states")

    op.drop_index(op.f("ix_agent_identities_created_by"), table_name="agent_identities")
    op.drop_index(
        op.f("ix_agent_identities_lifecycle_state"), table_name="agent_identities"
    )
    op.drop_index(op.f("ix_agent_identities_handle"), table_name="agent_identities")
    op.drop_index(op.f("ix_agent_identities_preset_id"), table_name="agent_identities")
    op.drop_index(op.f("ix_agent_identities_server_id"), table_name="agent_identities")
    op.drop_table("agent_identities")
