"""Drop the four legacy redesign tables (T13).

T23 migrated every router/service/repository to ``content_plans``, ``posts``,
``captions``, ``post_designs``, ``design_slides``, ``generated_images`` and
``image_resizes``. This contract revision removes ``generated_image``,
``design_structure``, ``post_structure`` and ``planning``. The downgrade
recreates them empty, as recorded in ADR-028: data is not restored.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0019_legacy_contract"
down_revision = "0018_campaign_persona_alignment"
branch_labels = None
depends_on = None

_TABLES = ("generated_image", "design_structure", "post_structure", "planning")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in _TABLES:
        if inspector.has_table(table):
            op.drop_table(table)


def downgrade() -> None:
    op.create_table(
        "planning",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("brand_id", uuid_pk, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("campaign_id", uuid_pk, sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("persona_id", uuid_pk, sa.ForeignKey("personas.id"), nullable=False),
        sa.Column("created_by", uuid_pk, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("persona_name", sa.String(30)),
        sa.Column("persona_age", sa.Integer()),
        sa.Column("persona_gender", sa.String(10)),
        sa.Column("persona_main_goal", sa.String(60)),
        sa.Column("persona_challenge", sa.String(50)),
        sa.Column("persona_interest", sa.String(200)),
        sa.Column("persona_routine", sa.String(300)),
        sa.Column("persona_journey", sa.String(250)),
        sa.Column("persona_trigger", sa.String(200)),
        sa.Column("planning_info", sa.String(400)),
        sa.Column("planning_static_amount", sa.Integer()),
        sa.Column("planning_carousel_amount", sa.Integer()),
        sa.Column("planning_stories_amount", sa.Integer()),
        sa.Column("planning_special_dates", sa.String(50)),
        sa.Column("planning_start_period", timestamp_tz),
        sa.Column("planning_end_period", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.create_table(
        "post_structure",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("planning_id", uuid_pk, sa.ForeignKey("planning.id"), nullable=False),
        sa.Column("created_by", uuid_pk, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_title", sa.String(100)),
        sa.Column("post_objective", sa.String(300)),
        sa.Column("post_big_idea", sa.String(150)),
        sa.Column("post_main_message", sa.String(150)),
        sa.Column("post_headline", sa.String(50)),
        sa.Column("image_cta", sa.String(30)),
        sa.Column("art_guiding", sa.String(1000)),
        sa.Column("post_status", sa.String(20)),
        sa.Column("content_format", sa.String(20)),
        sa.Column("art_ratio", sa.String(20)),
        sa.Column("art_resolution", sa.String(30)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.create_table(
        "design_structure",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "post_structure_id",
            uuid_pk,
            sa.ForeignKey("post_structure.id"),
            nullable=False,
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.create_table(
        "generated_image",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "design_structure_id",
            uuid_pk,
            sa.ForeignKey("design_structure.id"),
            nullable=False,
        ),
        sa.Column("signed_url", sa.String(2048)),
        sa.Column("size", sa.String(10)),
        sa.Column("resolution", sa.String(30)),
        sa.Column("image_ratio", sa.String(20)),
        sa.Column("image_status", sa.String(20)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
