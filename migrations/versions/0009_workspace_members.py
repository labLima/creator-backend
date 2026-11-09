"""Turn ``workspace_memberships`` into ``workspace_members``.

SQLite cannot rename or drop columns in place, and reflecting the old table
loses unnamed constraints, so the migration builds the target table and copies
the rows. Soft-deleted memberships have no representation in the final modeling
and are dropped with the old table. The role vocabulary is unchanged here; T21
migrates it.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0009_workspace_members"
down_revision = "0008_billing_credit_satellites"
branch_labels = None
depends_on = None

_COLUMNS = (
    "id",
    "workspace_id",
    "user_id",
    "role",
    "status",
    "invited_by",
    "created_at",
    "updated_at",
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("workspace_members"):
        # Fresh database: the baseline already created the final shape.
        return

    op.rename_table("workspace_memberships", "workspace_members")

    # Discarded memberships have child rows in invite usages and notification
    # recipients. Alembic does not enable SQLite foreign keys, so orphans would
    # survive silently (or abort the drop when the app engine enforces them).
    # Policy: a removed member's invite usage is dropped (the member is gone and
    # there is no restoration path), while the notification recipient is kept
    # and simply loses the reference.
    op.execute(
        "DELETE FROM workspace_invite_usages WHERE member_id IN ("
        "SELECT id FROM workspace_members WHERE deleted_at IS NOT NULL)"
    )
    op.execute(
        "UPDATE notification_recipients SET workspace_member_id = NULL "
        "WHERE workspace_member_id IN ("
        "SELECT id FROM workspace_members WHERE deleted_at IS NOT NULL)"
    )

    op.create_table(
        "workspace_members_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "status",
            enum_column("member_status"),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column(
            "invited_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO workspace_members_new "
        "(id, workspace_id, user_id, role, status, invited_by, created_at, updated_at) "
        "SELECT id, workspace_id, user_id, role, 'ACTIVE', NULL, created_at, updated_at "
        "FROM workspace_members WHERE deleted_at IS NULL"
    )
    op.drop_table("workspace_members")
    op.rename_table("workspace_members_new", "workspace_members")

    op.create_index(
        "uq_workspace_members_workspace_user",
        "workspace_members",
        ["workspace_id", "user_id"],
        unique=True,
    )
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    op.create_index(
        "ix_workspace_members_workspace_id_role",
        "workspace_members",
        ["workspace_id", "role"],
    )
    op.create_index("ix_workspace_members_invited_by", "workspace_members", ["invited_by"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workspace_members"):
        return

    op.rename_table("workspace_members", "workspace_memberships")
    op.create_table(
        "workspace_memberships_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_memberships_deleted_after_created",
        ),
    )
    op.execute(
        "INSERT INTO workspace_memberships_new "
        "(id, workspace_id, user_id, role, created_at, updated_at, deleted_at) "
        "SELECT id, workspace_id, user_id, role, created_at, updated_at, NULL "
        "FROM workspace_memberships"
    )
    op.drop_table("workspace_memberships")
    op.rename_table("workspace_memberships_new", "workspace_memberships")

    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])
    op.create_index(
        "ix_workspace_memberships_workspace_id", "workspace_memberships", ["workspace_id"]
    )
    op.create_index(
        "uq_workspace_memberships_active_user_workspace",
        "workspace_memberships",
        ["user_id", "workspace_id"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
