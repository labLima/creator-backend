"""Shared, database-portable SQLAlchemy scalar types.

SQLite is the default runtime database. These types keep the model layer free
of PostgreSQL-only constructs while preserving the UUID/JSON/UTC semantics the
application expects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import JSONB


class UTCDateTime(TypeDecorator[datetime]):
    """Persist timestamps as UTC and always return timezone-aware values.

    SQLite's ``DATETIME`` storage does not retain an offset. Normalising at the
    type boundary avoids naive/aware comparison bugs in repositories and tests.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


uuid_pk = Uuid(as_uuid=True)
uuid_default = uuid4
timestamp_tz = UTCDateTime()
json_type = JSON().with_variant(JSONB(), "postgresql")

__all__ = ["UTCDateTime", "json_type", "timestamp_tz", "uuid_default", "uuid_pk"]
