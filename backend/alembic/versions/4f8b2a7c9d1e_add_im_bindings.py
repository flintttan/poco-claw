"""add im bindings

Revision ID: 4f8b2a7c9d1e
Revises: 3c8e5f2b1a7d
Create Date: 2026-06-25 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f8b2a7c9d1e"
down_revision: Union[str, Sequence[str], None] = "3c8e5f2b1a7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add IM bindings + binding codes, backfill from auth_identities.

    The new model treats Poco ``users`` as the unique identity, with
    ``im_bindings`` as a many-to-many join from ``users.id`` to
    provider-specific user identifiers (Feishu open_id/union_id,
    DingTalk staffId, Telegram user.id, etc.). One IM identity can be
    bound to at most one Poco user, enforced by a UNIQUE constraint on
    ``(provider, im_user_id)``.

    ``im_binding_codes`` is a short-lived (10 min), single-use code
    table that bridges web-side OAuth (which knows the Poco user) to
    IM-side linking (which knows the IM identity but not the user).
    The web UI generates a code, the user types it in IM, and the
    inbound service consumes the code to create an ``im_bindings`` row.

    The migration also backfills ``im_bindings`` from the existing
    ``auth_identities`` table for any provider that supports both OAuth
    login and IM (currently just Feishu) so existing OAuth users get an
    IM binding automatically the first time they message the bot.
    """
    op.create_table(
        "im_bindings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("im_user_id", sa.String(length=255), nullable=False),
        sa.Column("im_union_id", sa.String(length=255), nullable=True),
        sa.Column("im_display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "bound_via",
            sa.String(length=32),
            server_default=sa.text("'code'"),
            nullable=False,
        ),
        sa.Column(
            "bound_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "im_user_id", name="uq_im_bindings_provider_im_user_id"
        ),
    )
    op.create_index(
        op.f("ix_im_bindings_user_id"),
        "im_bindings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_im_bindings_provider_im_union_id"),
        "im_bindings",
        ["provider", "im_union_id"],
        unique=True,
    )

    op.create_table(
        "im_binding_codes",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by", sa.String(length=255), nullable=True),
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_im_binding_codes_code"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_im_binding_codes_expires_at"),
        "im_binding_codes",
        ["expires_at"],
        unique=False,
    )

    # Backfill im_bindings from auth_identities for any provider that
    # supports both OAuth login AND IM (currently just Feishu). This
    # means existing OAuth users get an IM binding on the next inbound
    # message without having to go through the bind-code flow.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO im_bindings
                (user_id, provider, im_user_id, im_union_id, im_display_name,
                 bound_via, bound_at, created_at, updated_at)
            SELECT
                ai.user_id,
                ai.provider,
                COALESCE(
                    NULLIF(ai.profile_json ->> 'open_id', ''),
                    ai.provider_user_id
                ) AS im_user_id,
                NULLIF(ai.profile_json ->> 'union_id', '') AS im_union_id,
                NULLIF(ai.profile_json ->> 'name', '') AS im_display_name,
                'oauth_auto' AS bound_via,
                now(), now(), now()
            FROM auth_identities ai
            WHERE ai.provider IN ('feishu')
            ON CONFLICT (provider, im_user_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    """Remove IM bindings + binding codes tables."""
    op.drop_index(op.f("ix_im_binding_codes_expires_at"), table_name="im_binding_codes")
    op.drop_table("im_binding_codes")
    op.drop_index(op.f("ix_im_bindings_provider_im_union_id"), table_name="im_bindings")
    op.drop_index(op.f("ix_im_bindings_user_id"), table_name="im_bindings")
    op.drop_table("im_bindings")
