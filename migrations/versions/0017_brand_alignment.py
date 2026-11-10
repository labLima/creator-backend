"""Align ``brands``, ``brand_colors``, ``brand_assets`` and ``brand_settings``.

T25 first slice. The final modeling replaces the free-form brand description,
voice and JSON metadata with the explicit columns ``segment``, ``promise``,
``goals``, ``indicators``, ``inspirations`` and ``restrictions``. Colors become
``name``/``hex``/``position`` and assets become storage bucket/key pairs.

The old columns are folded into the new ones before the rebuild so existing
readers keep meaningful data. ``brand_settings`` also has its foreign key
narrowed to ``brands.id`` because the composite UNIQUE is removed.
"""

import json
import re
from urllib.parse import urlparse

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import hex_color_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import (
    json_type,
    timestamp_tz,
    uuid_pk,
)

revision = "0017_brand_alignment"
down_revision = "0016_identity_alignment"
branch_labels = None
depends_on = None

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_ASSET_TYPES = {"LOGO", "IMAGE", "FONT", "ICON", "DOCUMENT", "OTHER"}


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table)}


def _json_field(value: object, key: str) -> object | None:
    if not value:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    found = parsed.get(key)
    return str(found) if found is not None else None


def _rebuild_brand_settings() -> None:
    columns = _columns("brand_settings")
    if not columns:
        return
    op.create_table(
        "brand_settings_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("brand_id", uuid_pk, nullable=False),
        sa.Column("voice_settings", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("visual_settings", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("generation_defaults", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.UniqueConstraint("brand_id", name="uq_brand_settings_brand_id"),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"], name="fk_brand_settings_brand", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_brand_settings_deleted_after_created",
        ),
    )
    op.execute(
        "INSERT INTO brand_settings_old "
        "(id, workspace_id, brand_id, voice_settings, visual_settings, "
        "generation_defaults, metadata, created_at, updated_at, deleted_at) "
        "SELECT id, workspace_id, brand_id, voice_settings, visual_settings, "
        "generation_defaults, metadata, created_at, updated_at, deleted_at "
        "FROM brand_settings"
    )
    op.drop_table("brand_settings")
    op.rename_table("brand_settings_old", "brand_settings")
    op.create_index("ix_brand_settings_workspace_id", "brand_settings", ["workspace_id"])


def _rebuild_brands() -> None:
    columns = _columns("brands")
    if not columns or "created_by" in columns:
        return

    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, workspace_id, created_by_user_id, name, description, "
                "brand_voice, metadata, created_at, updated_at, deleted_at FROM brands"
            )
        )
    ]
    normalized: list[dict[str, object]] = []
    for row in rows:
        metadata = row["metadata"]
        normalized.append(
            {
                "id": row["id"],
                "workspace_id": row["workspace_id"],
                "created_by": row["created_by_user_id"],
                "name": str(row["name"])[:100],
                "segment": _json_field(metadata, "segment"),
                "promise": (str(row["description"])[:250] if row["description"] else None),
                "goals": _json_field(metadata, "goals"),
                "indicators": _json_field(metadata, "indicators"),
                "inspirations": _json_field(metadata, "inspirations")
                or (str(row["brand_voice"])[:1500] if row["brand_voice"] else None),
                "restrictions": _json_field(metadata, "restrictions"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
            }
        )

    op.create_table(
        "brands_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("segment", sa.String(100)),
        sa.Column("promise", sa.String(250)),
        sa.Column("goals", sa.String(1800)),
        sa.Column("indicators", sa.String(250)),
        sa.Column("inspirations", sa.String(1500)),
        sa.Column("restrictions", sa.String(200)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.UniqueConstraint("id", "workspace_id", name="uq_brands_id_workspace_id"),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO brands_old "
                "(id, workspace_id, created_by, name, segment, promise, goals, "
                "indicators, inspirations, restrictions, created_at, updated_at, deleted_at) "
                "VALUES (:id, :workspace_id, :created_by, :name, :segment, :promise, "
                ":goals, :indicators, :inspirations, :restrictions, :created_at, "
                ":updated_at, :deleted_at)"
            ),
            normalized,
        )
    op.drop_table("brands")
    op.rename_table("brands_old", "brands")
    op.create_index("ix_brands_workspace_id", "brands", ["workspace_id"])
    op.create_index(
        "idx_m8_brands_created_by",
        "brands",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def _rebuild_brand_colors() -> None:
    columns = _columns("brand_colors")
    if not columns or "hex" in columns:
        return

    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                'SELECT id, brand_id, color_name, hex_code, "order", created_at, updated_at '
                "FROM brand_colors"
            )
        )
    ]
    normalized = []
    for row in rows:
        hex_value = row["hex_code"]
        if not isinstance(hex_value, str) or not _HEX.match(hex_value):
            hex_value = "#000000"
        normalized.append(
            {
                "id": row["id"],
                "brand_id": row["brand_id"],
                "name": row["color_name"],
                "hex": hex_value,
                "position": row["order"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "brand_colors_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50)),
        sa.Column("hex", sa.String(7), nullable=False),
        sa.Column("position", sa.Integer()),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(hex_color_check("hex"), name="chk_brand_colors_hex"),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO brand_colors_old "
                "(id, brand_id, name, hex, position, created_at, updated_at) "
                "VALUES (:id, :brand_id, :name, :hex, :position, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("brand_colors")
    op.rename_table("brand_colors_old", "brand_colors")
    op.create_index("ix_brand_colors_brand_id", "brand_colors", ["brand_id"])


def _asset_storage(file_url: str, asset_id: str) -> tuple[str, str]:
    parsed = urlparse(file_url)
    if parsed.netloc and parsed.path:
        bucket = parsed.netloc[:63]
        key = parsed.path.lstrip("/")[:1024] or asset_id
        return bucket, key
    return "legacy", (file_url[:1024] or asset_id)


def _rebuild_brand_assets() -> None:
    columns = _columns("brand_assets")
    if not columns or "storage_key" in columns:
        return

    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, brand_id, type, file_url, file_name, description, "
                "created_at, updated_at, deleted_at FROM brand_assets"
            )
        )
    ]
    creator_by_brand = {
        str(row[0]): row[1]
        for row in op.get_bind().execute(sa.text("SELECT id, created_by FROM brands"))
    }
    seen: set[tuple[str, str]] = set()
    normalized = []
    for row in rows:
        if row["deleted_at"] is not None:
            continue
        asset_type = str(row["type"] or "OTHER").upper()
        if asset_type not in _ASSET_TYPES:
            asset_type = "OTHER"
        bucket, key = _asset_storage(str(row["file_url"] or ""), str(row["id"]))
        while (bucket, key) in seen:
            key = f"{key}~{row['id']}"
        seen.add((bucket, key))
        normalized.append(
            {
                "id": row["id"],
                "brand_id": row["brand_id"],
                "type": asset_type,
                "storage_bucket": bucket,
                "storage_key": key[:1024],
                "file_name": row["file_name"],
                "description": row["description"],
                "created_by": creator_by_brand.get(str(row["brand_id"])),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "brand_assets_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", enum_column("brand_asset_type"), nullable=False),
        sa.Column("storage_bucket", sa.String(63), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO brand_assets_old "
                "(id, brand_id, type, storage_bucket, storage_key, file_name, "
                "description, created_by, created_at, updated_at) "
                "VALUES (:id, :brand_id, :type, :storage_bucket, :storage_key, "
                ":file_name, :description, :created_by, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("brand_assets")
    op.rename_table("brand_assets_old", "brand_assets")
    op.create_index(
        "uq_brand_assets_storage_bucket_storage_key",
        "brand_assets",
        ["storage_bucket", "storage_key"],
        unique=True,
    )
    op.create_index("ix_brand_assets_brand_id", "brand_assets", ["brand_id"])
    op.create_index("ix_brand_assets_created_by", "brand_assets", ["created_by"])


def upgrade() -> None:
    _rebuild_brands()
    _rebuild_brand_settings()
    _rebuild_brand_colors()
    _rebuild_brand_assets()


def downgrade() -> None:
    """Recreate the pre-T25 shape.

    The downgrade restores the columns, not the exact original text: the old
    ``description``/``brand_voice``/``metadata`` are rebuilt from the explicit
    fields and ``file_url`` from bucket/key. That is enough for a rollback of
    the application, not for forensic recovery.
    """

    _downgrade_brand_assets()
    _downgrade_brand_colors()
    _downgrade_brand_settings()
    _downgrade_brands()


def _downgrade_brand_assets() -> None:
    columns = _columns("brand_assets")
    if not columns or "file_url" in columns:
        return
    op.create_table(
        "brand_assets_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("brand_id", uuid_pk, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("file_url", sa.String(2048), nullable=False),
        sa.Column("file_name", sa.String(255)),
        sa.Column("description", sa.String(500)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO brand_assets_legacy "
        "(id, brand_id, type, file_url, file_name, description, created_at, updated_at) "
        "SELECT id, brand_id, lower(type), storage_bucket || '/' || storage_key, "
        "file_name, description, created_at, updated_at FROM brand_assets"
    )
    op.drop_table("brand_assets")
    op.rename_table("brand_assets_legacy", "brand_assets")


def _downgrade_brand_colors() -> None:
    columns = _columns("brand_colors")
    if not columns or "hex_code" in columns:
        return
    op.create_table(
        "brand_colors_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("brand_id", uuid_pk, nullable=False),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("created_by", uuid_pk, nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("color_name", sa.String(50)),
        sa.Column("hex_code", sa.String(7)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO brand_colors_legacy "
        '(id, brand_id, workspace_id, created_by, "order", color_name, hex_code, '
        "created_at, updated_at) "
        "SELECT c.id, c.brand_id, b.workspace_id, COALESCE(b.created_by, c.brand_id), "
        "COALESCE(c.position, 0), c.name, c.hex, c.created_at, c.updated_at "
        "FROM brand_colors c JOIN brands b ON b.id = c.brand_id"
    )
    op.drop_table("brand_colors")
    op.rename_table("brand_colors_legacy", "brand_colors")


def _downgrade_brand_settings() -> None:
    columns = _columns("brand_settings")
    if not columns:
        return
    op.create_table(
        "brand_settings_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("brand_id", uuid_pk, nullable=False),
        sa.Column("voice_settings", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("visual_settings", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("generation_defaults", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO brand_settings_legacy "
        "(id, workspace_id, brand_id, voice_settings, visual_settings, "
        "generation_defaults, metadata, created_at, updated_at, deleted_at) "
        "SELECT id, workspace_id, brand_id, voice_settings, visual_settings, "
        "generation_defaults, metadata, created_at, updated_at, deleted_at "
        "FROM brand_settings"
    )
    op.drop_table("brand_settings")
    op.rename_table("brand_settings_legacy", "brand_settings")


def _downgrade_brands() -> None:
    columns = _columns("brands")
    if not columns or "created_by_user_id" in columns:
        return
    op.create_table(
        "brands_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("created_by_user_id", uuid_pk),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("brand_voice", sa.Text()),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.UniqueConstraint("id", "workspace_id", name="uq_brands_id_workspace_id"),
    )
    op.execute(
        "INSERT INTO brands_legacy "
        "(id, workspace_id, created_by_user_id, name, description, brand_voice, "
        "metadata, created_at, updated_at, deleted_at) "
        "SELECT id, workspace_id, created_by, name, promise, inspirations, "
        "json_object('segment', segment, 'goals', goals, 'indicators', indicators, "
        "'inspirations', inspirations, 'restrictions', restrictions), "
        "created_at, updated_at, deleted_at FROM brands"
    )
    op.drop_table("brands")
    op.rename_table("brands_legacy", "brands")
