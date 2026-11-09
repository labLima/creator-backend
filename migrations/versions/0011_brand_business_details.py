"""Add the campaign/persona parent keys and ``brand_business_details`` (T22).

``campaigns.brand_id`` is nullable here because the final modeling requires NOT
NULL and there is no source to backfill from yet; the gap stays in the parity
budget until T14. The two composite foreign keys of ``brand_business_details``
need the ``(id, brand_id)`` unique keys added in the same revision.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0011_brand_business_details"
down_revision = "0010_workspace_role_vocabulary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    campaign_columns = {column["name"] for column in inspector.get_columns("campaigns")}
    if inspector.has_table("brand_business_details") and "brand_id" in campaign_columns:
        # Fresh database (or a completed migration): the final shape is present.
        return
    brand_expression = "brand_id" if "brand_id" in campaign_columns else "NULL"

    # A column added with ``ALTER TABLE ... ADD COLUMN REFERENCES`` reflects
    # without its ON DELETE action, so the table is rebuilt with the final shape
    # (same strategy as the workspace_members migration).
    op.create_table(
        "campaigns_new",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("workspace_id", uuid_pk, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by", uuid_pk, sa.ForeignKey("users.id"), nullable=False),
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
        "INSERT INTO campaigns_new "
        "(id, brand_id, workspace_id, created_by, name, description, target_audience, "
        "objectives, voice, start_at, end_at, created_at, updated_at, deleted_at) "
        f"SELECT id, {brand_expression}, workspace_id, created_by, name, description, "
        "target_audience, "
        "objectives, voice, start_at, end_at, created_at, updated_at, deleted_at "
        "FROM campaigns"
    )
    op.drop_table("campaigns")
    op.rename_table("campaigns_new", "campaigns")
    op.create_index("uq_campaigns_id_brand_id", "campaigns", ["id", "brand_id"], unique=True)
    op.create_index("ix_campaigns_brand_id", "campaigns", ["brand_id"])

    op.create_index("uq_personas_id_brand_id", "personas", ["id", "brand_id"], unique=True)
    op.create_index("ix_personas_brand_id", "personas", ["brand_id"])

    op.create_table(
        "brand_business_details",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campaign_id", uuid_pk, nullable=False),
        sa.Column("persona_id", uuid_pk, nullable=False),
        sa.Column("output", json_type, nullable=False),
        sa.Column("model", sa.String(50)),
        sa.Column("spec_version", sa.String(50)),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["campaign_id", "brand_id"],
            ["campaigns.id", "campaigns.brand_id"],
            ondelete="CASCADE",
            name="fk_brand_business_details_campaign",
        ),
        sa.ForeignKeyConstraint(
            ["persona_id", "brand_id"],
            ["personas.id", "personas.brand_id"],
            ondelete="CASCADE",
            name="fk_brand_business_details_persona",
        ),
    )
    op.create_index(
        "ix_brand_business_details_brand_id_campaign_id_persona_id",
        "brand_business_details",
        ["brand_id", "campaign_id", "persona_id"],
    )
    op.create_index(
        "ix_brand_business_details_created_at", "brand_business_details", ["created_at"]
    )
    op.create_index(
        "idx_m8_brand_business_details_campaign_id_brand_id",
        "brand_business_details",
        ["campaign_id", "brand_id"],
    )
    op.create_index(
        "idx_m8_brand_business_details_persona_id_brand_id",
        "brand_business_details",
        ["persona_id", "brand_id"],
    )
    op.create_index(
        "idx_m8_brand_business_details_created_by",
        "brand_business_details",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("brand_business_details"):
        op.drop_table("brand_business_details")

    op.drop_index("ix_personas_brand_id", table_name="personas")
    op.drop_index("uq_personas_id_brand_id", table_name="personas")
    op.drop_index("ix_campaigns_brand_id", table_name="campaigns")
    op.drop_index("uq_campaigns_id_brand_id", table_name="campaigns")

    op.create_table(
        "campaigns_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by", uuid_pk, sa.ForeignKey("users.id"), nullable=False),
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
        "INSERT INTO campaigns_old "
        "(id, workspace_id, created_by, name, description, target_audience, objectives, "
        "voice, start_at, end_at, created_at, updated_at, deleted_at) "
        "SELECT id, workspace_id, created_by, name, description, target_audience, "
        "objectives, voice, start_at, end_at, created_at, updated_at, deleted_at "
        "FROM campaigns"
    )
    op.drop_table("campaigns")
    op.rename_table("campaigns_old", "campaigns")
