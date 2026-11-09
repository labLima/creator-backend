"""Migrate the workspace role vocabulary to the final modeling (ADR-028, T21).

``owner/admin/editor/viewer`` becomes ``OWNER/MANAGER/EDITOR/VIEWER``. The
``role`` column carries an inline CHECK built from the enum at creation time, so
SQLite cannot simply update the values: the table is rebuilt with the new CHECK
while the child foreign keys keep pointing at ``workspace_members``. Invite rows
store the same vocabulary in a plain varchar and are updated in place.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.enums import workspace_role_enum
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0010_workspace_role_vocabulary"
down_revision = "0009_workspace_members"
branch_labels = None
depends_on = None

_ROLE_UP = (
    "CASE role WHEN 'owner' THEN 'OWNER' WHEN 'admin' THEN 'MANAGER' "
    "WHEN 'editor' THEN 'EDITOR' WHEN 'viewer' THEN 'VIEWER' ELSE role END"
)
_ROLE_DOWN = (
    "CASE role WHEN 'OWNER' THEN 'owner' WHEN 'MANAGER' THEN 'admin' "
    "WHEN 'EDITOR' THEN 'editor' WHEN 'VIEWER' THEN 'viewer' ELSE role END"
)


def _create_members(table: str, role_type: sa.types.TypeEngine[object]) -> None:
    op.create_table(
        table,
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
        sa.Column("role", role_type, nullable=False),
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


def _create_indexes() -> None:
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


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workspace_members"):
        return

    _create_members("workspace_members_role_new", workspace_role_enum)
    op.execute(
        "INSERT INTO workspace_members_role_new "
        "(id, workspace_id, user_id, role, status, invited_by, created_at, updated_at) "
        f"SELECT id, workspace_id, user_id, {_ROLE_UP}, status, invited_by, "
        "created_at, updated_at FROM workspace_members"
    )
    op.drop_table("workspace_members")
    op.rename_table("workspace_members_role_new", "workspace_members")
    _create_indexes()

    if inspector.has_table("workspace_invites"):
        op.execute(f"UPDATE workspace_invites SET role = {_ROLE_UP}")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workspace_members"):
        return

    # The pre-T21 CHECK listed the lowercase values; SQLite cannot alter it, so
    # the rebuilt column keeps the values without that CHECK (irreversible detail
    # documented in ADR-028).
    _create_members("workspace_members_role_old", sa.String(20))
    op.execute(
        "INSERT INTO workspace_members_role_old "
        "(id, workspace_id, user_id, role, status, invited_by, created_at, updated_at) "
        f"SELECT id, workspace_id, user_id, {_ROLE_DOWN}, status, invited_by, "
        "created_at, updated_at FROM workspace_members"
    )
    op.drop_table("workspace_members")
    op.rename_table("workspace_members_role_old", "workspace_members")
    _create_indexes()

    if inspector.has_table("workspace_invites"):
        op.execute(f"UPDATE workspace_invites SET role = {_ROLE_DOWN}")
