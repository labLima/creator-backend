"""Create ``content_plans`` and its satellite tables (ADR-028, expand step T9).

The legacy ``planning`` table keeps its data until the contract step (T13); this
migration only adds the final-modeling shape next to it.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0012_content_plans"
down_revision = "0011_brand_business_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("content_plans"):
        # Fresh database: the baseline already created the final shape.
        return

    op.create_table(
        "content_plans",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "brand_id",
            uuid_pk,
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campaign_id", uuid_pk, nullable=False),
        sa.Column("persona_id", uuid_pk, nullable=False),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("briefing", sa.String(400)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.ForeignKeyConstraint(
            ["campaign_id", "brand_id"],
            ["campaigns.id", "campaigns.brand_id"],
            ondelete="CASCADE",
            name="fk_content_plans_campaign",
        ),
        sa.ForeignKeyConstraint(
            ["persona_id", "brand_id"],
            ["personas.id", "personas.brand_id"],
            ondelete="CASCADE",
            name="fk_content_plans_persona",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="chk_content_plans_period_order",
        ),
    )
    op.create_index("ix_content_plans_brand_id", "content_plans", ["brand_id"])
    op.create_index("ix_content_plans_campaign_id", "content_plans", ["campaign_id"])
    op.create_index("ix_content_plans_persona_id", "content_plans", ["persona_id"])
    op.create_index(
        "idx_m8_content_plans_campaign_id_brand_id",
        "content_plans",
        ["campaign_id", "brand_id"],
    )
    op.create_index(
        "idx_m8_content_plans_persona_id_brand_id",
        "content_plans",
        ["persona_id", "brand_id"],
    )
    op.create_index(
        "idx_m8_content_plans_created_by",
        "content_plans",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )

    op.create_table(
        "content_plan_items",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "content_plan_id",
            uuid_pk,
            sa.ForeignKey("content_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", enum_column("content_format"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity >= 0", name="ck_content_plan_items_quantity"),
    )
    op.create_index(
        "uq_content_plan_items_content_plan_id_format",
        "content_plan_items",
        ["content_plan_id", "format"],
        unique=True,
    )

    op.create_table(
        "content_plan_special_dates",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "content_plan_id",
            uuid_pk,
            sa.ForeignKey("content_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("special_date", sa.Date, nullable=False),
        sa.Column("label", sa.String(50)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_content_plan_special_dates_plan_date_label",
        "content_plan_special_dates",
        ["content_plan_id", "special_date", "label"],
        unique=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in (
        "content_plan_special_dates",
        "content_plan_items",
        "content_plans",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
