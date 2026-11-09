"""Allow an IMAGE Content Version to originate from an upload."""

import sqlalchemy as sa
from alembic import op

revision = "0006_imported_image_versions"
down_revision = "0005_content_text_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns("images")}
    if all(columns[name]["nullable"] for name in ("generation_id", "model", "prompt")):
        return
    with op.batch_alter_table("images") as batch:
        batch.alter_column(
            "generation_id", existing_type=columns["generation_id"]["type"], nullable=True
        )
        batch.alter_column("model", existing_type=sa.String(255), nullable=True)
        batch.alter_column("prompt", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM images WHERE generation_id IS NULL "
            "OR model IS NULL OR prompt IS NULL"
        )
    ).scalar_one():
        raise RuntimeError("Cannot downgrade while imported image versions exist")
    columns = {c["name"]: c for c in sa.inspect(connection).get_columns("images")}
    with op.batch_alter_table("images") as batch:
        batch.alter_column(
            "generation_id", existing_type=columns["generation_id"]["type"], nullable=False
        )
        batch.alter_column("model", existing_type=sa.String(255), nullable=False)
        batch.alter_column("prompt", existing_type=sa.Text(), nullable=False)
