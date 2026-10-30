"""Freeze the persistence schema so a file move cannot drop a table.

`alembic check` alone cannot detect a table lost during the refactor:
`migrations/versions/0001_sqlite_baseline.py` builds the database with
`Base.metadata.create_all()`. A fresh database is therefore created from the
same metadata the check compares against, so a forgotten import produces no
diff at all. These assertions are the real guard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from creator.infrastructure.database import models as _models  # noqa: F401  (registers tables)
from creator.infrastructure.database.db import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"


def _frozen_tables() -> list[str]:
    return json.loads((CONTRACTS / "schema_tables.json").read_text(encoding="utf-8"))


def _normalize(statement: str) -> str:
    return re.sub(r"\s+", " ", statement).strip()


def test_metadata_table_set_is_exact() -> None:
    """Equality, not subset: the existing guard accepts silent table loss."""
    assert sorted(Base.metadata.tables) == _frozen_tables()


def test_mappers_configure() -> None:
    """String foreign keys resolve lazily; split model files can break ordering."""
    configure_mappers()


def test_ddl_is_byte_identical() -> None:
    dialect = sa.dialects.sqlite.dialect()
    current = "\n\n".join(
        _normalize(str(CreateTable(table).compile(dialect=dialect)))
        for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name)
    )
    current_text = _normalize(current)
    frozen = _normalize((CONTRACTS / "schema_ddl.sql").read_text(encoding="utf-8"))

    assert current_text == frozen


def test_create_all_succeeds_on_sqlite() -> None:
    """Catches unresolved foreign keys that only surface at CREATE TABLE time."""
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    configure_mappers()
    engine.dispose()
