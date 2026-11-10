"""Align identity and invite tables to ``Creator_DB_final.sql`` (T24, second slice).

Changes:

- ``users``: ``external_id`` is absorbed by ``auth_provider_id`` (local
  synthetic ids become NULL), ``cpf``/``cnpj`` are dropped, ``email`` becomes
  ``varchar(254)`` with a partial UNIQUE on active rows, ``display_name``
  becomes NOT NULL. ``password_hash``/``global_role`` stay as the ADR-020
  exception.
- ``workspace_invites``: the plaintext ``token`` becomes ``token_hash``
  (SHA-256 hex, per the dump comment), ``role``/``type``/``status`` become the
  final enum vocabulary, ``uses_count``/``is_active``/``deleted_at`` are
  dropped. ``is_active = false`` and soft-deleted rows become
  ``status = 'REVOKED'``.
- ``workspace_invite_usages``: ``user_id``/``workspace_id`` are derived from
  ``member_id`` and therefore dropped; ``member_id`` becomes NOT NULL.

SQLite cannot drop columns in place, so the three tables are rebuilt. A fresh
database already has the final shape from ``0001_sqlite_baseline``; the guards
make the migration a no-op there.
"""

import hashlib

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0016_identity_alignment"
down_revision = "0015_notification_alignment"
branch_labels = None
depends_on = None


def _columns(table: str) -> dict[str, dict[str, object]]:
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def _rows(statement: str) -> list[dict[str, object]]:
    return [dict(row._mapping) for row in op.get_bind().execute(sa.text(statement))]


def _rebuild_users() -> None:
    if "auth_provider_id" in _columns("users"):
        return

    op.execute(
        "UPDATE users SET display_name = substr(COALESCE(email, 'creator'), 1, "
        "CASE WHEN instr(COALESCE(email, ''), '@') > 1 "
        "THEN instr(email, '@') - 1 ELSE 50 END) "
        "WHERE display_name IS NULL OR trim(display_name) = ''"
    )
    op.create_table(
        "users_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("auth_provider_id", sa.String()),
        sa.Column("email", sa.String(254)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("bio", sa.String(350)),
        sa.Column("avatar_url", sa.String()),
        sa.Column(
            "global_role",
            sa.Enum(
                "admin",
                "gestor",
                "membro",
                name="global_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default=sa.text("'membro'"),
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO users_new "
        "(id, auth_provider_id, email, password_hash, display_name, bio, avatar_url, "
        "global_role, created_at, updated_at, deleted_at) "
        "SELECT id, CASE WHEN external_id LIKE 'local:%' THEN NULL ELSE external_id END, "
        "substr(email, 1, 254), password_hash, substr(display_name, 1, 50), bio, avatar_url, "
        "global_role, created_at, updated_at, deleted_at FROM users"
    )
    op.drop_table("users")
    op.rename_table("users_new", "users")
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def _normalize_invite_rows() -> list[dict[str, object]]:
    """Read invites, hash tokens and normalize values before the rebuild.

    The old CHECKs allowed every combination, so the target constraints need a
    deterministic normalization: email invites without an email are dropped,
    link invites keep no email, link invites get ``max_uses = 1`` when missing
    and email invites lose ``max_uses``.
    """

    rows = _rows(
        "SELECT id, workspace_id, type, role, email, token, max_uses, status, "
        "created_by, expires_at, last_used_at, revoked_at, created_at, updated_at, "
        "is_active, deleted_at FROM workspace_invites"
    )
    normalized: list[dict[str, object]] = []
    seen_tokens: set[str] = set()
    for row in rows:
        invite_type = str(row["type"] or "LINK").upper()
        email = row["email"]
        if invite_type == "EMAIL" and not email:
            continue
        if invite_type == "LINK":
            email = None
        elif row["max_uses"] is not None:
            row["max_uses"] = None
        if invite_type == "LINK" and row["max_uses"] is None:
            row["max_uses"] = 1
        token_hash = hashlib.sha256(str(row["token"] or "").encode("utf-8")).hexdigest()
        if token_hash in seen_tokens:
            continue
        seen_tokens.add(token_hash)
        status = str(row["status"] or "PENDING").upper()
        if not bool(row["is_active"]) or row["deleted_at"] is not None:
            status = "REVOKED"
            row["revoked_at"] = row["revoked_at"] or row["deleted_at"]
        if status not in {"PENDING", "ACCEPTED", "REVOKED", "EXPIRED"}:
            status = "PENDING"
        row.update(
            {
                "type": invite_type,
                "role": str(row["role"]).upper(),
                "email": email,
                "token_hash": token_hash,
                "status": status,
            }
        )
        normalized.append(row)
    return normalized


def _rebuild_invites() -> None:
    if "token_hash" in _columns("workspace_invites"):
        return

    rows = _normalize_invite_rows()
    op.create_table(
        "workspace_invites_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", enum_column("invite_type"), nullable=False),
        sa.Column("role", enum_column("workspace_role"), nullable=False),
        sa.Column("email", sa.String(254)),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("max_uses", sa.Integer()),
        sa.Column(
            "status",
            enum_column("invite_status"),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("last_used_at", timestamp_tz),
        sa.Column("revoked_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_workspace_invites_token_hash"),
        sa.CheckConstraint(
            "(type = 'EMAIL') = (email IS NOT NULL)",
            name="chk_workspace_invites_email_by_type",
        ),
        sa.CheckConstraint(
            "(type = 'LINK') = (max_uses IS NOT NULL)",
            name="chk_workspace_invites_max_uses_by_type",
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR max_uses >= 1",
            name="chk_workspace_invites_max_uses_positive",
        ),
    )
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO workspace_invites_new "
                "(id, workspace_id, type, role, email, token_hash, max_uses, status, "
                "created_by, expires_at, last_used_at, revoked_at, created_at, updated_at) "
                "VALUES (:id, :workspace_id, :type, :role, :email, :token_hash, :max_uses, "
                ":status, :created_by, :expires_at, :last_used_at, :revoked_at, "
                ":created_at, :updated_at)"
            ),
            rows,
        )
    op.drop_table("workspace_invites")
    op.rename_table("workspace_invites_new", "workspace_invites")
    op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"])
    op.create_index("ix_workspace_invites_email", "workspace_invites", ["email"])
    op.create_index("ix_workspace_invites_status", "workspace_invites", ["status"])
    op.create_index("idx_m8_workspace_invites_created_by", "workspace_invites", ["created_by"])


def _member_for_usage(row: dict[str, object]) -> str | None:
    if row["member_id"] is not None:
        return str(row["member_id"])
    if row["user_id"] is None or row["workspace_id"] is None:
        return None
    found = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT id FROM workspace_members WHERE user_id = :user_id "
                "AND workspace_id = :workspace_id ORDER BY created_at LIMIT 1"
            ),
            {"user_id": row["user_id"], "workspace_id": row["workspace_id"]},
        )
        .scalar_one_or_none()
    )
    return str(found) if found else None


def _rebuild_usages() -> None:
    columns = _columns("workspace_invite_usages")
    if "user_id" not in columns:
        return

    rows = _rows(
        "SELECT id, invite_id, user_id, workspace_id, member_id, used_at, "
        "created_at, updated_at, deleted_at FROM workspace_invite_usages "
        "WHERE deleted_at IS NULL"
    )
    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        member_id = _member_for_usage(row)
        if member_id is None:
            continue
        key = (str(row["invite_id"]), member_id)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "id": row["id"],
                "invite_id": row["invite_id"],
                "member_id": member_id,
                "used_at": row["used_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "workspace_invite_usages_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "invite_id",
            uuid_pk,
            sa.ForeignKey("workspace_invites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            uuid_pk,
            sa.ForeignKey("workspace_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("used_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO workspace_invite_usages_new "
                "(id, invite_id, member_id, used_at, updated_at) "
                "VALUES (:id, :invite_id, :member_id, :used_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("workspace_invite_usages")
    op.rename_table("workspace_invite_usages_new", "workspace_invite_usages")
    op.create_index(
        "uq_workspace_invite_usages_invite_member",
        "workspace_invite_usages",
        ["invite_id", "member_id"],
        unique=True,
    )
    op.create_index(
        "ix_workspace_invite_usages_member_id", "workspace_invite_usages", ["member_id"]
    )


def upgrade() -> None:
    _rebuild_users()
    _rebuild_invites()
    _rebuild_usages()


def downgrade() -> None:
    """Recreate the pre-T24 shape; the plaintext tokens are not recoverable."""

    _downgrade_usages()
    _downgrade_invites()
    _downgrade_users()


def _downgrade_usages() -> None:
    columns = _columns("workspace_invite_usages")
    if "user_id" in columns:
        return
    op.create_table(
        "workspace_invite_usages_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("invite_id", uuid_pk, nullable=False),
        sa.Column("user_id", uuid_pk, nullable=False),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("member_id", uuid_pk),
        sa.Column("used_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO workspace_invite_usages_old "
        "(id, invite_id, user_id, workspace_id, member_id, used_at, created_at, updated_at) "
        "SELECT u.id, u.invite_id, m.user_id, m.workspace_id, u.member_id, u.used_at, "
        "u.used_at, u.updated_at FROM workspace_invite_usages u "
        "JOIN workspace_members m ON m.id = u.member_id"
    )
    op.drop_table("workspace_invite_usages")
    op.rename_table("workspace_invite_usages_old", "workspace_invite_usages")


def _downgrade_invites() -> None:
    if "token" in _columns("workspace_invites"):
        return
    op.create_table(
        "workspace_invites_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("max_uses", sa.Integer()),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", uuid_pk, nullable=False),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("last_used_at", timestamp_tz),
        sa.Column("revoked_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO workspace_invites_old "
        "(id, workspace_id, type, role, email, token, max_uses, uses_count, status, "
        "is_active, created_by, expires_at, last_used_at, revoked_at, created_at, updated_at) "
        "SELECT id, workspace_id, lower(type), lower(role), email, token_hash, max_uses, "
        "0, lower(status), CASE WHEN status = 'REVOKED' THEN 0 ELSE 1 END, created_by, "
        "expires_at, last_used_at, revoked_at, created_at, updated_at FROM workspace_invites"
    )
    op.drop_table("workspace_invites")
    op.rename_table("workspace_invites_old", "workspace_invites")


def _downgrade_users() -> None:
    if "external_id" in _columns("users"):
        return
    op.create_table(
        "users_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("display_name", sa.String(50)),
        sa.Column("cpf", sa.String(11)),
        sa.Column("cnpj", sa.String(14)),
        sa.Column("bio", sa.String(350)),
        sa.Column("avatar_url", sa.String()),
        sa.Column(
            "global_role",
            sa.Enum(
                "admin",
                "gestor",
                "membro",
                name="global_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default=sa.text("'membro'"),
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.UniqueConstraint("external_id", name="uq_users_external_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.execute(
        "INSERT INTO users_old "
        "(id, external_id, email, password_hash, display_name, bio, avatar_url, "
        "global_role, created_at, updated_at, deleted_at) "
        "SELECT id, COALESCE(auth_provider_id, 'restored:' || id), email, password_hash, "
        "display_name, bio, avatar_url, global_role, created_at, updated_at, deleted_at "
        "FROM users"
    )
    op.drop_table("users")
    op.rename_table("users_old", "users")
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
