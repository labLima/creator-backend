"""Create audit_logs, user_consents and persona_interests.

First slice of the final-modeling alignment (ADR-028): three tables with no
dependency on the redesigned content/media model. Each table is guarded
separately because the historical baseline creates the whole current metadata
on a fresh database; an interrupted upgrade must not be marked complete.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0006_audit_consent_persona"
down_revision = "0005_content_text_versions"
branch_labels = None
depends_on = None


def _missing(table: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _missing("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "actor_id",
                uuid_pk,
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "workspace_id",
                uuid_pk,
                sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", uuid_pk, nullable=False),
            sa.Column("before", json_type),
            sa.Column("after", json_type),
            sa.Column("ip_address", sa.String(45)),
            sa.Column("user_agent", sa.String(255)),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_audit_logs_entity_type_entity_id_created_at",
            "audit_logs",
            ["entity_type", "entity_id", "created_at"],
        )
        op.create_index(
            "ix_audit_logs_actor_id_created_at", "audit_logs", ["actor_id", "created_at"]
        )
        op.create_index(
            "ix_audit_logs_workspace_id_created_at",
            "audit_logs",
            ["workspace_id", "created_at"],
        )
        op.create_index("ix_audit_logs_action_created_at", "audit_logs", ["action", "created_at"])

    if _missing("user_consents"):
        op.create_table(
            "user_consents",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "user_id",
                uuid_pk,
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("type", enum_column("consent_type"), nullable=False),
            sa.Column("document_version", sa.String(20), nullable=False),
            sa.Column("granted", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("granted_at", timestamp_tz),
            sa.Column("revoked_at", timestamp_tz),
            sa.Column("ip_address", sa.String(45)),
            sa.Column("user_agent", sa.String(255)),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_user_consents_user_id_type_document_version",
            "user_consents",
            ["user_id", "type", "document_version"],
            unique=True,
        )

    if _missing("persona_interests"):
        op.create_table(
            "persona_interests",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "persona_id",
                uuid_pk,
                sa.ForeignKey("personas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("interest", sa.String(100), nullable=False),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "uq_persona_interests_persona_id_interest",
            "persona_interests",
            ["persona_id", "interest"],
            unique=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("persona_interests", "user_consents", "audit_logs"):
        if inspector.has_table(table):
            op.drop_table(table)
