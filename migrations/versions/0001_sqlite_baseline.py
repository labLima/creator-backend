"""Create the portable SQLite baseline from the SQLAlchemy metadata.

The pre-SQLite PostgreSQL migrations are archived under
``migrations/legacy_postgres``. This baseline is intentionally generated from
the model metadata so the SQLite schema and the ORM cannot drift at inception.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from creator.infrastructure.database import models as _models  # noqa: F401
from creator.infrastructure.database.db import Base

revision = "0001_sqlite_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
