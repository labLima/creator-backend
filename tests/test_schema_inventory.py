"""Freeze the persistence schema so a file move cannot drop a table.

`alembic check` alone cannot detect a table lost during the refactor:
`migrations/versions/0001_sqlite_baseline.py` builds the database with
`Base.metadata.create_all()`. A fresh database is therefore created from the
same metadata the check compares against, so a forgotten import produces no
diff at all. These assertions are the real guard.

The parity block compares the metadata against the final modeling dump using the
same module the report script uses (``creator.infrastructure.database.final_schema``).
Divergences are tracked in ``schema_parity_budget.json``: the budget may only
shrink, so every PR that fixes a table lowers a count in the same diff.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from creator.infrastructure.database import metadata as _models  # noqa: F401  (registers tables)
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.final_schema import (
    CHECK_MAP,
    GAP_CATEGORIES,
    RENAME_MAP,
    FinalSchema,
    Gap,
    compare,
    gap_counts,
    gap_digest,
    parse_final,
    parse_models,
    sha256_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
FINAL_DUMP = PROJECT_ROOT / "docs" / "migration" / "Creator_DB_final.sql"
PARITY_FIXTURE = CONTRACTS / "creator_db_final.sql"
BUDGET = json.loads((CONTRACTS / "schema_parity_budget.json").read_text(encoding="utf-8"))


def _frozen_tables() -> list[str]:
    return json.loads((CONTRACTS / "schema_tables.json").read_text(encoding="utf-8"))


def _normalize(statement: str) -> str:
    return re.sub(r"\s+", " ", statement).strip()


def _final() -> FinalSchema:
    return parse_final(PARITY_FIXTURE.read_text(encoding="utf-8"))


def _gap() -> Gap:
    return compare(_final(), parse_models(Base.metadata))


def _budget_problems(
    actual: dict[str, int],
    expected: dict[str, int],
    categories: tuple[str, ...],
) -> list[str]:
    problems: list[str] = []
    for category in categories:
        current = actual[category]
        allowed = expected[category]
        if current > allowed:
            problems.append(
                f"{category}: schema debt GREW from {allowed} to {current}; "
                "the budget may only shrink"
            )
        elif current < allowed:
            problems.append(
                f"{category}: ratchet stale ({allowed} budgeted, {current} actual); "
                "lower the budget in this PR"
            )
    return problems


def _assert_budget(categories: tuple[str, ...]) -> None:
    actual = gap_counts(_gap())
    problems = _budget_problems(actual, BUDGET["counts"], categories)
    assert not problems, "\n".join(problems)


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


# --- Final-modeling parity -------------------------------------------------


def test_parity_fixture_matches_versioned_dump() -> None:
    """The fixture must be the same bytes as the versioned modeling."""
    dump_hash = sha256_file(FINAL_DUMP)
    assert sha256_file(PARITY_FIXTURE) == dump_hash, (
        "tests/contracts/creator_db_final.sql diverged from "
        "docs/migration/Creator_DB_final.sql; recopy it"
    )
    assert BUDGET["dump_sha256"] == dump_hash, "budget dump_sha256 is stale"
    assert BUDGET["fixture_sha256"] == dump_hash, "budget fixture_sha256 is stale"


def test_parity_tables() -> None:
    _assert_budget(("table_missing", "table_extra"))


def test_parity_columns_and_primary_keys() -> None:
    _assert_budget(("pk_mismatch", "column_missing", "column_extra"))


def test_parity_types_nullability_and_defaults() -> None:
    _assert_budget(("nullability", "width", "default_missing"))


def test_parity_enum_vocabulary() -> None:
    _assert_budget(("enum",))


def test_parity_indexes() -> None:
    _assert_budget(("index_missing", "index_extra", "index_name"))


def test_parity_foreign_keys() -> None:
    _assert_budget(("fk_missing", "fk_extra", "fk_ondelete"))


def test_parity_checks() -> None:
    _assert_budget(("check_missing", "check_extra"))


def test_parity_budget_digest_matches() -> None:
    """Any change in the gap requires updating the budget in the same PR."""
    actual = gap_digest(_gap())
    assert actual == BUDGET["gap_digest"], (
        "parity budget is stale: regenerate tests/contracts/schema_parity_budget.json "
        "and review the diff"
    )


def test_parity_budget_covers_every_category() -> None:
    assert tuple(BUDGET["counts"]) == GAP_CATEGORIES
    assert set(BUDGET["counts"].values()) >= {0}


def test_ratchet_mechanism_detects_growth_and_stagnation() -> None:
    """The guard itself must fail on growth and on a stale budget."""
    baseline = {"column_missing": 10, "enum": 0}
    assert _budget_problems(baseline, baseline, ("column_missing", "enum")) == []

    grew = _budget_problems({"column_missing": 11, "enum": 0}, baseline, ("column_missing",))
    assert grew and "GREW" in grew[0]

    stale = _budget_problems({"column_missing": 9, "enum": 0}, baseline, ("column_missing",))
    assert stale and "stale" in stale[0]


def test_rename_map_is_applied_once() -> None:
    """A renamed table must not appear as both missing and extra."""
    final = _final()
    gap = compare(final, parse_models(Base.metadata))
    for final_name, model_name in RENAME_MAP.items():
        assert model_name in final.tables or model_name in Base.metadata.tables
        assert final_name not in gap.details.get("table_missing", [])
        assert model_name not in gap.details.get("table_extra", [])


def test_check_map_entries_are_well_formed() -> None:
    """Every CHECK_MAP entry must point at a real dump check and a real model check."""
    final = _final()
    models = parse_models(Base.metadata)
    known_checks = {
        f"{table_name}.{check_name}"
        for table_name, table in final.tables.items()
        for check_name, _expression in table.checks
    }
    for key, target in CHECK_MAP.items():
        assert key in known_checks, f"{key} is not a CHECK of the final modeling"
        target_table, _, target_name = target.partition(".")
        assert target_table in models, f"{target} points at an unknown table"
        names = {name for name, _sqltext in models[target_table].checks if name}
        assert target_name in names, f"{target} points at an unknown model constraint"
