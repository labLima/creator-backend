"""Create ``posts``, ``captions``, ``post_designs`` and ``design_slides`` (T10).

Expand step of the editorial redesign: the legacy ``post_structure`` and
``design_structure`` tables keep their data until the contract step (T13).
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0013_posts_captions_designs"
down_revision = "0012_content_plans"
branch_labels = None
depends_on = None


def _missing(table: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _missing("posts"):
        _create_posts()
    if _missing("captions"):
        _create_captions()
    if _missing("post_designs"):
        _create_post_designs()
    if _missing("design_slides"):
        _create_design_slides()


def _create_posts() -> None:
    op.create_table(
        "posts",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "content_plan_id",
            uuid_pk,
            sa.ForeignKey("content_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(100)),
        sa.Column("objective", sa.String(300)),
        sa.Column("big_idea", sa.String(150)),
        sa.Column("main_message", sa.String(150)),
        sa.Column(
            "publication_status",
            enum_column("publication_status"),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column(
            "approval_status",
            enum_column("approval_status"),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "approved_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", timestamp_tz),
        sa.Column("rejection_reason", sa.String(500)),
        sa.Column("scheduled_at", timestamp_tz),
        sa.Column("published_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.CheckConstraint(
            "(approved_at IS NULL) = (approved_by IS NULL)",
            name="chk_posts_approval_pair",
        ),
        sa.CheckConstraint(
            "approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL",
            name="chk_posts_rejected_reason",
        ),
        sa.CheckConstraint(
            "approval_status <> 'APPROVED' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_posts_approved_metadata",
        ),
        sa.CheckConstraint(
            "publication_status <> 'SCHEDULED' OR scheduled_at IS NOT NULL",
            name="chk_posts_scheduled_at",
        ),
        sa.CheckConstraint(
            "publication_status <> 'PUBLISHED' OR published_at IS NOT NULL",
            name="chk_posts_published_at",
        ),
        sa.CheckConstraint(
            "publication_status = 'DRAFT' OR approval_status = 'APPROVED'",
            name="chk_posts_publish_requires_approval",
        ),
    )
    op.create_index(
        "ix_posts_content_plan_id_publication_status",
        "posts",
        ["content_plan_id", "publication_status"],
    )
    op.create_index(
        "ix_posts_content_plan_id_created_at", "posts", ["content_plan_id", "created_at"]
    )
    op.create_index("ix_posts_publication_status", "posts", ["publication_status"])
    op.create_index("ix_posts_approval_status", "posts", ["approval_status"])
    op.create_index("ix_posts_scheduled_at", "posts", ["scheduled_at"])
    op.create_index("ix_posts_approved_by", "posts", ["approved_by"])
    op.create_index(
        "idx_m8_posts_created_by",
        "posts",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )


def _create_captions() -> None:
    op.create_table(
        "captions",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "post_id",
            uuid_pk,
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version >= 1", name="ck_captions_version"),
    )
    op.create_index("uq_captions_post_id_version", "captions", ["post_id", "version"], unique=True)
    # The dump's predicate also references `deleted_at`, a column `captions`
    # does not have; filtering on is_current keeps the invariant enforceable.
    op.create_index(
        "uq_captions_current",
        "captions",
        ["post_id"],
        unique=True,
        sqlite_where=sa.text("is_current"),
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "idx_m8_captions_created_by",
        "captions",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )


def _create_post_designs() -> None:
    op.create_table(
        "post_designs",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "post_id",
            uuid_pk,
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", enum_column("content_format"), nullable=False),
        sa.Column("ratio", enum_column("art_ratio"), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "format <> 'STORIES' OR ratio = 'RATIO_9_16'",
            name="chk_post_designs_stories_ratio",
        ),
    )
    op.create_index("ix_post_designs_post_id", "post_designs", ["post_id"])


def _create_design_slides() -> None:
    op.create_table(
        "design_slides",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "post_design_id",
            uuid_pk,
            sa.ForeignKey("post_designs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("headline", sa.String(50)),
        sa.Column("subtitle", sa.String(40)),
        sa.Column("cta", sa.String(30)),
        sa.Column("art_direction", sa.String(1000), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("position >= 0", name="ck_design_slides_position"),
    )
    op.create_index(
        "uq_design_slides_post_design_id_position",
        "design_slides",
        ["post_design_id", "position"],
        unique=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in (
        "design_slides",
        "post_designs",
        "captions",
        "posts",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
