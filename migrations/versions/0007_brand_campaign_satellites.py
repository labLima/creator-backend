"""Create the brand and campaign satellite tables (ADR-028, slice T6).

``brand_business_details`` stays out of this slice: its composite foreign keys
require ``campaigns.brand_id`` and the ``(id, brand_id)`` unique keys, which land
with the campaigns alignment (T14).
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0007_brand_campaign_satellites"
down_revision = "0006_audit_consent_persona"
branch_labels = None
depends_on = None


def _missing(table: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _missing("brand_hashtags"):
        op.create_table(
            "brand_hashtags",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "brand_id",
                uuid_pk,
                sa.ForeignKey("brands.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("hashtag", sa.String(100), nullable=False),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_brand_hashtags_brand_id_hashtag",
            "brand_hashtags",
            ["brand_id", "hashtag"],
            unique=True,
        )

    if _missing("brand_values"):
        op.create_table(
            "brand_values",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "brand_id",
                uuid_pk,
                sa.ForeignKey("brands.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("value", sa.String(100), nullable=False),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_brand_values_brand_id_value", "brand_values", ["brand_id", "value"], unique=True
        )

    if _missing("campaign_hashtags"):
        op.create_table(
            "campaign_hashtags",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "campaign_id",
                uuid_pk,
                sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("hashtag", sa.String(60), nullable=False),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_campaign_hashtags_campaign_id_hashtag",
            "campaign_hashtags",
            ["campaign_id", "hashtag"],
            unique=True,
        )

    if _missing("campaign_voices"):
        op.create_table(
            "campaign_voices",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "campaign_id",
                uuid_pk,
                sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("voice", enum_column("campaign_voice"), nullable=False),
            sa.Column("created_by", uuid_pk, nullable=True),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_campaign_voices_campaign_id_voice",
            "campaign_voices",
            ["campaign_id", "voice"],
            unique=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("campaign_voices", "campaign_hashtags", "brand_values", "brand_hashtags"):
        if inspector.has_table(table):
            op.drop_table(table)
