"""Align ``campaigns`` and ``personas`` to the final modeling (T25).

Campaigns lose ``workspace_id`` (derived from ``brands``), the period columns
and the free-form ``voice`` (moved to ``campaign_voices``), gain
``expected_action`` and require ``brand_id``. Existing campaigns get their brand
from the legacy ``planning`` row, or from a brand in the same workspace; the
migration aborts with an explicit list when neither source exists.

Personas map the numeric ``age`` to ``age_range``, ``trigger`` to
``trigger_event``, validate ``gender`` against the final vocabulary and move the
free-form ``interest`` to ``persona_interests``.
"""

import uuid

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import (
    CAMPAIGN_VOICE,
    enum_column,
)
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0018_campaign_persona_alignment"
down_revision = "0017_brand_alignment"
branch_labels = None
depends_on = None

_AGE_RANGES = (
    (17, "UP_TO_17"),
    (24, "FROM_18_TO_24"),
    (34, "FROM_25_TO_34"),
    (44, "FROM_35_TO_44"),
    (54, "FROM_45_TO_54"),
    (64, "FROM_55_TO_64"),
)
_GENDERS = {"MALE", "FEMALE", "NON_BINARY", "OTHER", "PREFER_NOT_TO_SAY"}


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table)}


def _age_range(age: object) -> str | None:
    if not isinstance(age, int):
        return None
    for limit, value in _AGE_RANGES:
        if age <= limit:
            return value
    return "FROM_65_PLUS"


def _backfill_campaign_brands() -> list[str]:
    op.execute(
        "UPDATE campaigns SET brand_id = ("
        "SELECT brand_id FROM planning WHERE planning.campaign_id = campaigns.id LIMIT 1"
        ") WHERE brand_id IS NULL"
    )
    op.execute(
        "UPDATE campaigns SET brand_id = ("
        "SELECT id FROM brands WHERE brands.workspace_id = campaigns.workspace_id "
        "AND brands.deleted_at IS NULL ORDER BY created_at LIMIT 1"
        ") WHERE brand_id IS NULL OR brand_id NOT IN ("
        "SELECT id FROM brands WHERE brands.workspace_id = campaigns.workspace_id)"
    )
    missing = [
        str(row[0])
        for row in op.get_bind().execute(sa.text("SELECT id FROM campaigns WHERE brand_id IS NULL"))
    ]
    if missing:
        raise RuntimeError(
            "campaigns without a brand cannot be migrated to NOT NULL: " + ", ".join(missing)
        )
    return missing


def _migrate_campaign_voices() -> None:
    columns = _columns("campaign_voices")
    if not columns:
        return
    rows = op.get_bind().execute(
        sa.text("SELECT id, voice, created_by FROM campaigns WHERE voice IS NOT NULL")
    )
    seen: set[tuple[object, str]] = set()
    for campaign_id, voice, created_by in rows:
        normalized = str(voice).upper()
        if normalized not in CAMPAIGN_VOICE or (campaign_id, normalized) in seen:
            continue
        seen.add((campaign_id, normalized))
        op.get_bind().execute(
            sa.text(
                "INSERT INTO campaign_voices "
                "(id, campaign_id, voice, created_by, created_at, updated_at) "
                "VALUES (:id, :campaign_id, :voice, :created_by, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid.uuid4().hex,
                "campaign_id": campaign_id,
                "voice": normalized,
                "created_by": created_by,
            },
        )


def _rebuild_campaigns() -> None:
    columns = _columns("campaigns")
    if not columns or "expected_action" in columns:
        return

    _backfill_campaign_brands()
    _migrate_campaign_voices()
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, brand_id, created_by, name, description, target_audience, "
                "objectives, created_at, updated_at, deleted_at FROM campaigns"
            )
        )
    ]
    normalized = [
        {
            **row,
            "name": str(row["name"])[:100],
        }
        for row in rows
    ]
    op.create_table(
        "campaigns_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("target_audience", sa.String(300)),
        sa.Column("objectives", sa.String(400)),
        sa.Column("expected_action", sa.String(250)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO campaigns_old "
                "(id, brand_id, created_by, name, description, target_audience, "
                "objectives, created_at, updated_at, deleted_at) "
                "VALUES (:id, :brand_id, :created_by, :name, :description, "
                ":target_audience, :objectives, :created_at, :updated_at, :deleted_at)"
            ),
            normalized,
        )
    op.drop_table("campaigns")
    op.rename_table("campaigns_old", "campaigns")
    op.create_index("uq_campaigns_id_brand_id", "campaigns", ["id", "brand_id"], unique=True)
    op.create_index("ix_campaigns_brand_id", "campaigns", ["brand_id"])
    op.create_index(
        "idx_m8_campaigns_created_by",
        "campaigns",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def _migrate_persona_interests() -> None:
    if not _columns("persona_interests"):
        return
    rows = op.get_bind().execute(
        sa.text("SELECT id, interest FROM personas WHERE interest IS NOT NULL AND interest <> ''")
    )
    seen: set[tuple[object, str]] = set()
    for persona_id, interest in rows:
        value = str(interest)[:100]
        if (persona_id, value) in seen:
            continue
        seen.add((persona_id, value))
        op.get_bind().execute(
            sa.text(
                "INSERT INTO persona_interests "
                "(id, persona_id, interest, created_at, updated_at) "
                "VALUES (:id, :persona_id, :interest, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid.uuid4().hex,
                "persona_id": persona_id,
                "interest": value,
            },
        )


def _rebuild_personas() -> None:
    columns = _columns("personas")
    if not columns or "age_range" in columns:
        return

    _migrate_persona_interests()
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, created_by, brand_id, name, age, gender, main_goal, "
                "challenge, routine, journey, trigger, created_at, updated_at, deleted_at "
                "FROM personas"
            )
        )
    ]
    normalized = []
    for row in rows:
        gender = str(row["gender"]).upper() if row["gender"] else None
        normalized.append(
            {
                "id": row["id"],
                "created_by": row["created_by"],
                "brand_id": row["brand_id"],
                "name": str(row["name"])[:100],
                "age_range": _age_range(row["age"]),
                "gender": gender if gender in _GENDERS else None,
                "main_goal": row["main_goal"],
                "challenge": row["challenge"],
                "routine": row["routine"],
                "journey": row["journey"],
                "trigger_event": row["trigger"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
            }
        )
    op.create_table(
        "personas_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("age_range", enum_column("age_range")),
        sa.Column("gender", enum_column("persona_gender")),
        sa.Column("main_goal", sa.String(60)),
        sa.Column("challenge", sa.String(50)),
        sa.Column("routine", sa.String(300)),
        sa.Column("journey", sa.String(250)),
        sa.Column("trigger_event", sa.String(200)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO personas_old "
                "(id, created_by, brand_id, name, age_range, gender, main_goal, "
                "challenge, routine, journey, trigger_event, created_at, updated_at, "
                "deleted_at) "
                "VALUES (:id, :created_by, :brand_id, :name, :age_range, :gender, "
                ":main_goal, :challenge, :routine, :journey, :trigger_event, "
                ":created_at, :updated_at, :deleted_at)"
            ),
            normalized,
        )
    op.drop_table("personas")
    op.rename_table("personas_old", "personas")
    op.create_index("uq_personas_id_brand_id", "personas", ["id", "brand_id"], unique=True)
    op.create_index("ix_personas_brand_id", "personas", ["brand_id"])
    op.create_index(
        "idx_m8_personas_created_by",
        "personas",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def upgrade() -> None:
    _rebuild_campaigns()
    _rebuild_personas()


def downgrade() -> None:
    """Recreate the pre-T25 shape with lossy reconstructions.

    ``campaigns.workspace_id`` is recovered from the brand, ``voice`` from the
    first ``campaign_voices`` row, periods stay NULL and ``personas.age`` is
    recovered from the middle of the age range. The exact values are gone.
    """

    _downgrade_personas()
    _downgrade_campaigns()


def _downgrade_personas() -> None:
    columns = _columns("personas")
    if not columns or "age" in columns:
        return
    op.create_table(
        "personas_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("brand_id", uuid_pk, nullable=False),
        sa.Column("created_by", uuid_pk, nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("gender", sa.String(10)),
        sa.Column("main_goal", sa.String(60)),
        sa.Column("challenge", sa.String(50)),
        sa.Column("interest", sa.String(200)),
        sa.Column("routine", sa.String(300)),
        sa.Column("journey", sa.String(250)),
        sa.Column("trigger", sa.String(200)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO personas_legacy "
        "(id, brand_id, created_by, name, gender, main_goal, challenge, routine, "
        "journey, trigger, created_at, updated_at, deleted_at) "
        "SELECT id, brand_id, COALESCE(created_by, brand_id), name, lower(gender), "
        "main_goal, challenge, routine, journey, trigger_event, created_at, "
        "updated_at, deleted_at FROM personas"
    )
    op.drop_table("personas")
    op.rename_table("personas_legacy", "personas")
    op.create_index("uq_personas_id_brand_id", "personas", ["id", "brand_id"], unique=True)
    op.create_index("ix_personas_brand_id", "personas", ["brand_id"])


def _downgrade_campaigns() -> None:
    columns = _columns("campaigns")
    if not columns or "workspace_id" in columns:
        return
    op.create_table(
        "campaigns_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("brand_id", uuid_pk),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("created_by", uuid_pk, nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("target_audience", sa.String(300)),
        sa.Column("objectives", sa.String(400)),
        sa.Column("voice", sa.String(20)),
        sa.Column("start_at", timestamp_tz),
        sa.Column("end_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO campaigns_legacy "
        "(id, brand_id, workspace_id, created_by, name, description, target_audience, "
        "objectives, voice, created_at, updated_at, deleted_at) "
        "SELECT c.id, c.brand_id, b.workspace_id, COALESCE(c.created_by, c.brand_id), "
        "c.name, c.description, c.target_audience, c.objectives, "
        "(SELECT lower(voice) FROM campaign_voices WHERE campaign_id = c.id LIMIT 1), "
        "c.created_at, c.updated_at, c.deleted_at "
        "FROM campaigns c JOIN brands b ON b.id = c.brand_id"
    )
    op.drop_table("campaigns")
    op.rename_table("campaigns_legacy", "campaigns")
    op.create_index("uq_campaigns_id_brand_id", "campaigns", ["id", "brand_id"], unique=True)
    op.create_index("ix_campaigns_brand_id", "campaigns", ["brand_id"])
