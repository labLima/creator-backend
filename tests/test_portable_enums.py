"""Portable enum vocabulary and index naming helpers.

The vocabulary must match ``docs/migration/Creator_DB_final.sql`` exactly, and
the rendered column must stay SQLite-compatible: VARCHAR plus CHECK, never a
native enum type.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from creator.infrastructure.database.final_schema import parse_final
from creator.infrastructure.database.naming import (
    MAX_IDENTIFIER_LENGTH,
    index_name,
    unique_index_name,
)
from creator.infrastructure.database.portable_enums import ENUMS, enum_column

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_DUMP = PROJECT_ROOT / "docs" / "migration" / "Creator_DB_final.sql"


def _dump_enums() -> dict[str, tuple[str, ...]]:
    return parse_final(FINAL_DUMP.read_text(encoding="utf-8")).enums


def test_enum_inventory_matches_final_modeling() -> None:
    """Every dump enum exists with the same values, and nothing extra."""
    expected = _dump_enums()
    assert set(ENUMS) == set(expected)
    mismatches = {
        name: (expected[name], ENUMS[name])
        for name in sorted(expected)
        if tuple(expected[name]) != tuple(ENUMS[name])
    }
    assert not mismatches, mismatches


def test_enum_column_renders_varchar_and_check() -> None:
    metadata = sa.MetaData()
    table = sa.Table(
        "demo",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", enum_column("member_status"), nullable=False),
    )
    ddl = str(sa.schema.CreateTable(table).compile(dialect=sa.dialects.sqlite.dialect()))

    assert "VARCHAR" in ddl.upper()
    assert "CHECK" in ddl.upper()
    assert "ACTIVE" in ddl
    assert "CREATE TYPE" not in ddl.upper()
    assert "member_status" in ddl


def test_enum_column_rejects_values_outside_the_vocabulary() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "demo",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", enum_column("member_status"), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert().values(id=1, status="ACTIVE"))
        with pytest.raises(IntegrityError):
            connection.execute(sa.text("INSERT INTO demo (id, status) VALUES (2, 'NOT_A_STATUS')"))
    engine.dispose()


def test_enum_column_unknown_name_fails_loudly() -> None:
    with pytest.raises(KeyError, match="unknown enum"):
        enum_column("does_not_exist")


def test_index_names_are_deterministic_and_prefixed() -> None:
    assert index_name("brands", ("workspace_id",)) == "ix_brands_workspace_id"
    assert index_name("brands", ("workspace_id", "deleted_at")) == (
        "ix_brands_workspace_id_deleted_at"
    )
    assert unique_index_name("brands", ("workspace_id", "name")) == ("uq_brands_workspace_id_name")
    assert index_name("brands", ("workspace_id",)) == index_name("brands", ("workspace_id",))


def test_long_index_names_stay_within_the_identifier_limit() -> None:
    columns = tuple(f"column_{index}" for index in range(12))
    name = index_name("a_very_long_table_name_for_testing", columns)
    assert len(name) <= MAX_IDENTIFIER_LENGTH
    assert name.startswith("ix_a_very_long_table_name_for_testing_")
