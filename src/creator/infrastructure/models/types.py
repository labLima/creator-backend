"""Shared SQLAlchemy scalar types used by the infrastructure boundary.

The types in this module intentionally use SQLAlchemy's generic types.  The
PostgreSQL deployment can still optimize them through its dialect, while
SQLite remains usable for local development and schema tests.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Uuid
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class UTCDateTime(TypeDecorator[datetime]):
    """Store aware datetimes normalized to UTC on every supported dialect."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[datetime]:
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


uuid_pk = Uuid(as_uuid=True)
uuid_default = uuid4
json_type = JSON()
timestamp_tz = UTCDateTime()

__all__ = [
    "UTCDateTime",
    "json_type",
    "timestamp_tz",
    "uuid_default",
    "uuid_pk",
]
