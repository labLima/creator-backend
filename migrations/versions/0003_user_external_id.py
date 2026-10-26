"""Rename user external identity column.

Revision ID: 0003_user_external_id
Revises: 0002_initial_relational_model
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_user_external_id"
down_revision: str | Sequence[str] | None = "0002_initial_relational_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("uq_users_auth_subject", type_="unique")
            batch.alter_column("auth_subject", new_column_name="external_id")
        op.create_index("uq_users_external_id", "users", ["external_id"], unique=True)
        return

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_auth_subject", type_="unique")
        batch.alter_column("auth_subject", new_column_name="external_id")
        batch.create_unique_constraint("uq_users_external_id", ["external_id"])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.drop_index("uq_users_external_id", table_name="users")
        with op.batch_alter_table("users") as batch:
            batch.alter_column("external_id", new_column_name="auth_subject")
        op.create_index("uq_users_auth_subject", "users", ["auth_subject"], unique=True)
        return

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_external_id", type_="unique")
        batch.alter_column("external_id", new_column_name="auth_subject")
        batch.create_unique_constraint("uq_users_auth_subject", ["auth_subject"])
