"""Create ``generated_images`` and ``image_resizes`` (ADR-028, expand step T11).

Completes the final-modeling table set; the legacy ``generated_image`` table
keeps its data until the contract step (T13).
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0014_generated_images"
down_revision = "0013_posts_captions_designs"
branch_labels = None
depends_on = None


def _missing(table: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _missing("generated_images"):
        _create_generated_images()
    if _missing("image_resizes"):
        _create_image_resizes()


def _create_generated_images() -> None:
    op.create_table(
        "generated_images",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "design_slide_id",
            uuid_pk,
            sa.ForeignKey("design_slides.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_bucket", sa.String(63)),
        sa.Column("storage_key", sa.String(1024)),
        sa.Column(
            "mime_type", sa.String(127), nullable=False, server_default=sa.text("'image/png'")
        ),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("model", sa.String(50)),
        sa.Column("prompt", sa.String),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.String),
        sa.Column(
            "generation_status",
            enum_column("generation_status"),
            nullable=False,
            server_default=sa.text("'GENERATING'"),
        ),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("false")),
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
        sa.Column("feedback_type", enum_column("image_feedback_type")),
        sa.Column("feedback_text", sa.String(1000)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.CheckConstraint(
            "NOT is_current OR (generation_status = 'SUCCEEDED' AND deleted_at IS NULL)",
            name="chk_generated_images_current_complete",
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0", name="chk_generated_images_size_bytes"
        ),
        sa.CheckConstraint(
            "width IS NULL OR height IS NULL OR (width > 0 AND height > 0)",
            name="chk_generated_images_dimensions",
        ),
        sa.CheckConstraint(
            "(approved_at IS NULL) = (approved_by IS NULL)",
            name="chk_generated_images_approval_pair",
        ),
        sa.CheckConstraint(
            "approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL",
            name="chk_generated_images_rejected_reason",
        ),
        sa.CheckConstraint(
            "approval_status <> 'APPROVED' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_generated_images_approved_metadata",
        ),
        sa.CheckConstraint(
            "approval_status = 'PENDING' OR generation_status = 'SUCCEEDED'",
            name="chk_generated_images_approval_after_generation",
        ),
        sa.CheckConstraint(
            "generation_status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL "
            "AND storage_key IS NOT NULL AND size_bytes IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="chk_generated_images_file_by_status",
        ),
        sa.CheckConstraint(
            "generation_status <> 'FAILED' OR error_message IS NOT NULL",
            name="chk_generated_images_failed_message",
        ),
    )
    op.create_index(
        "uq_generated_images_current_per_slide",
        "generated_images",
        ["design_slide_id"],
        unique=True,
        sqlite_where=sa.text("is_current AND deleted_at IS NULL"),
        postgresql_where=sa.text("is_current AND deleted_at IS NULL"),
    )
    op.create_index("ix_generated_images_design_slide_id", "generated_images", ["design_slide_id"])
    op.create_index(
        "ix_generated_images_generation_status", "generated_images", ["generation_status"]
    )
    op.create_index("ix_generated_images_approval_status", "generated_images", ["approval_status"])
    op.create_index("ix_generated_images_approved_by", "generated_images", ["approved_by"])
    op.create_index(
        "uq_generated_images_storage_bucket_storage_key",
        "generated_images",
        ["storage_bucket", "storage_key"],
        unique=True,
    )
    op.create_index(
        "idx_m8_generated_images_created_by",
        "generated_images",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )


def _create_image_resizes() -> None:
    op.create_table(
        "image_resizes",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "source_image_id",
            uuid_pk,
            sa.ForeignKey("generated_images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ratio", enum_column("art_ratio"), nullable=False),
        sa.Column(
            "status",
            enum_column("resize_status"),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("storage_bucket", sa.String(63)),
        sa.Column("storage_key", sa.String(1024)),
        sa.Column("mime_type", sa.String(127)),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("error_message", sa.String),
        sa.Column(
            "created_by",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL "
            "AND storage_key IS NOT NULL AND size_bytes IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="chk_image_resizes_file",
        ),
        sa.CheckConstraint(
            "status <> 'FAILED' OR error_message IS NOT NULL",
            name="chk_image_resizes_failed",
        ),
        sa.CheckConstraint("size_bytes IS NULL OR size_bytes > 0", name="chk_image_resizes_size"),
        sa.CheckConstraint(
            "(width IS NULL OR width > 0) AND (height IS NULL OR height > 0)",
            name="chk_image_resizes_dimensions",
        ),
    )
    op.create_index("ix_image_resizes_source_image_id", "image_resizes", ["source_image_id"])
    op.create_index(
        "uq_image_resizes_storage_bucket_storage_key",
        "image_resizes",
        ["storage_bucket", "storage_key"],
        unique=True,
    )
    op.create_index(
        "idx_image_resizes_created_by",
        "image_resizes",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("image_resizes", "generated_images"):
        if inspector.has_table(table):
            op.drop_table(table)
