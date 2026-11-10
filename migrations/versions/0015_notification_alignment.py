"""Align the notification tables to ``Creator_DB_final.sql`` (T24 first slice).

The final modeling has no ``deleted_at`` on these tables and does not keep
``workspace_member_id`` or ``provider_message_id``. SQLite cannot drop columns
in place, so each table is rebuilt and the rows are copied. Soft-deleted rows
are dropped because the target has no representation for them; duplicate keys
that would violate the new UNIQUE indexes are resolved deterministically
(keep the oldest notification, keep the newest device/preference/recipient).

The migration is guarded per table: a fresh database has the final shape from
``0001_sqlite_baseline`` and must not be rebuilt (and lose data) again.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import (
    json_type,
    timestamp_tz,
    uuid_pk,
)

revision = "0015_notification_alignment"
down_revision = "0014_generated_images"
branch_labels = None
depends_on = None


def _columns(table: str) -> dict[str, dict[str, object]]:
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def _rebuild_devices() -> None:
    if "deleted_at" not in _columns("user_devices"):
        return

    op.execute(
        "DELETE FROM user_devices WHERE fcm_token IN ("
        "SELECT fcm_token FROM user_devices GROUP BY fcm_token HAVING COUNT(*) > 1)"
        " AND rowid NOT IN ("
        "SELECT MAX(rowid) FROM user_devices GROUP BY fcm_token)"
    )
    op.create_table(
        "user_devices_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", enum_column("device_platform"), nullable=False),
        sa.Column("fcm_token", sa.String(255), nullable=False),
        sa.UniqueConstraint("fcm_token", name="uq_user_devices_fcm_token"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO user_devices_new "
        "(id, user_id, platform, fcm_token, is_active, last_seen_at, created_at, updated_at) "
        "SELECT id, user_id, platform, fcm_token, is_active, last_seen_at, created_at, updated_at "
        "FROM user_devices WHERE deleted_at IS NULL"
    )
    op.drop_table("user_devices")
    op.rename_table("user_devices_new", "user_devices")
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"])


def _rebuild_preferences() -> None:
    if "deleted_at" not in _columns("notification_preferences"):
        return

    op.execute(
        "DELETE FROM notification_preferences WHERE rowid NOT IN ("
        "SELECT MAX(rowid) FROM notification_preferences GROUP BY user_id, type, channel)"
    )
    op.create_table(
        "notification_preferences_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", enum_column("notification_type"), nullable=False),
        sa.Column("channel", enum_column("notification_channel"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO notification_preferences_new "
        "(id, user_id, type, channel, is_enabled, created_at, updated_at) "
        "SELECT id, user_id, type, channel, is_enabled, created_at, updated_at "
        "FROM notification_preferences WHERE deleted_at IS NULL"
    )
    op.drop_table("notification_preferences")
    op.rename_table("notification_preferences_new", "notification_preferences")
    op.create_index(
        "uq_notification_preferences_user_type_channel",
        "notification_preferences",
        ["user_id", "type", "channel"],
        unique=True,
    )


def _rebuild_notifications() -> None:
    columns = _columns("notifications")
    if "deleted_at" not in columns:
        return

    op.execute(
        "UPDATE notifications SET dedupe_key = NULL "
        "WHERE dedupe_key IS NOT NULL AND rowid NOT IN ("
        "SELECT MIN(rowid) FROM notifications "
        "WHERE dedupe_key IS NOT NULL GROUP BY workspace_id, dedupe_key)"
    )
    op.create_table(
        "notifications_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", enum_column("notification_type"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.String(2000), nullable=True),
        sa.Column("payload", json_type, nullable=True),
        sa.Column("resource_type", enum_column("notification_resource_type")),
        sa.Column("resource_id", uuid_pk),
        sa.Column("dedupe_key", sa.String(128)),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(resource_type IS NULL) = (resource_id IS NULL)",
            name="chk_notifications_resource_pair",
        ),
    )
    op.execute(
        "INSERT INTO notifications_new "
        "(id, workspace_id, type, title, body, payload, resource_type, resource_id, "
        "dedupe_key, created_by, created_at, updated_at) "
        "SELECT id, workspace_id, type, title, body, payload, resource_type, resource_id, "
        "dedupe_key, created_by, created_at, updated_at "
        "FROM notifications WHERE deleted_at IS NULL"
    )
    op.drop_table("notifications")
    op.rename_table("notifications_new", "notifications")
    op.create_index(
        "uq_notifications_workspace_dedupe",
        "notifications",
        ["workspace_id", "dedupe_key"],
        unique=True,
    )
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index(
        "idx_m8_notifications_created_by",
        "notifications",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def _rebuild_recipients() -> None:
    columns = _columns("notification_recipients")
    if "external_message_id" in columns:
        return

    column_names = ", ".join(columns)
    assert "provider_message_id" in columns, column_names
    op.execute(
        "DELETE FROM notification_recipients WHERE rowid NOT IN ("
        "SELECT MAX(rowid) FROM notification_recipients "
        "GROUP BY notification_id, user_id, channel)"
    )
    op.create_table(
        "notification_recipients_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "notification_id",
            uuid_pk,
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", enum_column("notification_channel"), nullable=False),
        sa.Column(
            "status",
            enum_column("notification_delivery_status"),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("external_message_id", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_at", timestamp_tz),
        sa.Column("read_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO notification_recipients_new "
        "(id, notification_id, user_id, channel, status, external_message_id, "
        "error_message, attempts, sent_at, read_at, created_at, updated_at) "
        "SELECT id, notification_id, user_id, channel, status, provider_message_id, "
        "error_message, attempts, sent_at, read_at, created_at, updated_at "
        "FROM notification_recipients WHERE deleted_at IS NULL"
    )
    op.drop_table("notification_recipients")
    op.rename_table("notification_recipients_new", "notification_recipients")
    op.create_index(
        "ix_notification_recipients_user_channel",
        "notification_recipients",
        ["user_id", "channel"],
    )
    op.create_index(
        "ix_notification_recipients_user_read_at",
        "notification_recipients",
        ["user_id", "read_at"],
    )
    op.create_index(
        "ix_notification_recipients_user_created_at",
        "notification_recipients",
        ["user_id", "created_at"],
    )
    op.create_index(
        "uq_notification_recipients_notification_user_channel",
        "notification_recipients",
        ["notification_id", "user_id", "channel"],
        unique=True,
    )


def upgrade() -> None:
    _rebuild_devices()
    _rebuild_preferences()
    _rebuild_notifications()
    _rebuild_recipients()


def downgrade() -> None:
    """Recreate the pre-T24 shape.

    The downgrade restores the columns, not the soft-deleted rows: the upgrade
    drops them because the final modeling has no representation for them.
    """

    _downgrade_recipients()
    _downgrade_notifications()
    _downgrade_preferences()
    _downgrade_devices()


def _downgrade_recipients() -> None:
    if "external_message_id" not in _columns("notification_recipients"):
        return

    op.create_table(
        "notification_recipients_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("notification_id", uuid_pk, nullable=False),
        sa.Column("user_id", uuid_pk, nullable=False),
        sa.Column("workspace_member_id", uuid_pk),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_message_id", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_at", timestamp_tz),
        sa.Column("read_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO notification_recipients_old "
        "(id, notification_id, user_id, channel, status, provider_message_id, "
        "error_message, attempts, sent_at, read_at, created_at, updated_at) "
        "SELECT id, notification_id, user_id, channel, status, external_message_id, "
        "error_message, attempts, sent_at, read_at, created_at, updated_at "
        "FROM notification_recipients"
    )
    op.drop_table("notification_recipients")
    op.rename_table("notification_recipients_old", "notification_recipients")


def _downgrade_notifications() -> None:
    if "deleted_at" in _columns("notifications"):
        return

    op.create_table(
        "notifications_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", uuid_pk),
        sa.Column("dedupe_key", sa.String(128)),
        sa.Column("created_by", uuid_pk),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO notifications_old "
        "(id, workspace_id, type, title, body, payload, resource_type, resource_id, "
        "dedupe_key, created_by, created_at, updated_at) "
        "SELECT id, workspace_id, type, title, COALESCE(body, ''), COALESCE(payload, '{}'), "
        "resource_type, resource_id, dedupe_key, created_by, created_at, updated_at "
        "FROM notifications"
    )
    op.drop_table("notifications")
    op.rename_table("notifications_old", "notifications")


def _downgrade_preferences() -> None:
    if "deleted_at" in _columns("notification_preferences"):
        return

    op.create_table(
        "notification_preferences_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("user_id", uuid_pk, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO notification_preferences_old "
        "(id, user_id, type, channel, is_enabled, created_at, updated_at) "
        "SELECT id, user_id, type, channel, is_enabled, created_at, updated_at "
        "FROM notification_preferences"
    )
    op.drop_table("notification_preferences")
    op.rename_table("notification_preferences_old", "notification_preferences")


def _downgrade_devices() -> None:
    if "deleted_at" in _columns("user_devices"):
        return

    op.create_table(
        "user_devices_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("user_id", uuid_pk, nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("fcm_token", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO user_devices_old "
        "(id, user_id, platform, fcm_token, is_active, last_seen_at, created_at, updated_at) "
        "SELECT id, user_id, platform, fcm_token, is_active, last_seen_at, created_at, updated_at "
        "FROM user_devices"
    )
    op.drop_table("user_devices")
    op.rename_table("user_devices_old", "user_devices")
