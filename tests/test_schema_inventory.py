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
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.orm import configure_mappers

from creator.infrastructure.database import metadata as _models  # noqa: F401  (registers tables)
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.final_schema import (
    ADR_EXTENSIONS,
    CHECK_MAP,
    GAP_CATEGORIES,
    LEGACY_RETENTION,
    NO_TARGET,
    RENAME_MAP,
    FinalSchema,
    Gap,
    compare,
    gap_counts,
    gap_digest,
    parse_final,
    parse_models,
    render_schema_ddl,
    sha256_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
FINAL_DUMP = PROJECT_ROOT / "docs" / "migration" / "Creator_DB_final.sql"
PARITY_FIXTURE = CONTRACTS / "creator_db_final.sql"
BUDGET = json.loads((CONTRACTS / "schema_parity_budget.json").read_text(encoding="utf-8"))


def _frozen_tables() -> list[str]:
    return json.loads((CONTRACTS / "schema_tables.json").read_text(encoding="utf-8"))


def _canonical(text: str) -> str:
    """Normalise only line endings and trailing whitespace."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalised.split("\n")).strip() + "\n"


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
    """Canonical bytes, tables and indexes: a formatting drift must fail too."""
    current_text = _canonical(render_schema_ddl(Base.metadata))
    frozen = _canonical((CONTRACTS / "schema_ddl.sql").read_text(encoding="utf-8"))

    assert current_text == frozen


def test_ddl_snapshot_includes_indexes() -> None:
    """Without indexes an index-only change would be invisible in the snapshot."""
    frozen = (CONTRACTS / "schema_ddl.sql").read_text(encoding="utf-8")
    assert "CREATE INDEX" in frozen


PREV_SCHEMA = CONTRACTS / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"


def test_upgrade_from_previous_schema_converges(tmp_path: Path) -> None:
    """A forgotten revision must fail: the DB is built from the previous schema.

    ``0001_sqlite_baseline`` creates the schema from ``Base.metadata``, so a
    database upgraded from scratch is always self-consistent. This test builds
    the database from the committed previous schema, stamps it at the previous
    head and upgrades: only the new revisions run, exactly like a real database.
    """
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    database = tmp_path / "previous.db"
    url = f"sqlite+pysqlite:///{database}"
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            "CREATE TABLE alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        connection.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (?)", (PREV_REVISION,)
        )

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert diff == [], diff


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


PARITY_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "tables": ("table_missing", "table_extra", "allowlisted", "rename_collision"),
    "columns": ("pk_mismatch", "column_missing", "column_extra"),
    "types": ("nullability", "width", "kind", "default_missing", "default_value"),
    "enums": ("enum",),
    "uniques": ("unique_missing", "unique_extra"),
    "indexes": ("index_missing", "index_extra", "index_name"),
    "foreign_keys": ("fk_missing", "fk_extra", "fk_ondelete"),
    "checks": ("check_missing", "check_extra"),
}


@pytest.mark.parametrize("dimension", sorted(PARITY_DIMENSIONS))
def test_parity_dimension(dimension: str) -> None:
    _assert_budget(PARITY_DIMENSIONS[dimension])


def test_parity_covers_every_category() -> None:
    """A new category must be assigned to a dimension, not silently ignored."""
    covered = {category for categories in PARITY_DIMENSIONS.values() for category in categories}
    assert covered == set(GAP_CATEGORIES), sorted(set(GAP_CATEGORIES) - covered)


def test_parity_budget_digest_matches() -> None:
    """Any change in the gap requires updating the budget in the same PR."""
    actual = gap_digest(_gap())
    assert actual == BUDGET["gap_digest"], (
        "parity budget is stale: regenerate tests/contracts/schema_parity_budget.json "
        "and review the diff"
    )


def test_parity_budget_covers_every_category() -> None:
    assert tuple(BUDGET["counts"]) == GAP_CATEGORIES


def test_ratchet_mechanism_detects_growth_and_stagnation() -> None:
    """The guard itself must fail on growth and on a stale budget."""
    baseline = {"column_missing": 10, "enum": 0}
    assert _budget_problems(baseline, baseline, ("column_missing", "enum")) == []

    grew = _budget_problems({"column_missing": 11, "enum": 0}, baseline, ("column_missing",))
    assert grew and "GREW" in grew[0]

    stale = _budget_problems({"column_missing": 9, "enum": 0}, baseline, ("column_missing",))
    assert stale and "stale" in stale[0]


def test_rename_map_is_applied_once() -> None:
    """A mapped table must not appear as both missing and extra.

    The map is empty once names align; the assertion still guards a future entry.
    """
    final = _final()
    gap = compare(final, parse_models(Base.metadata))
    for final_name, model_name in RENAME_MAP.items():
        assert model_name in Base.metadata.tables
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
        target_path, expected_sql = target
        target_table, _, target_name = target_path.partition(".")
        assert target_table in models, f"{target_path} points at an unknown table"
        names = {name for name, _sqltext in models[target_table].checks if name}
        assert target_name in names, f"{target_path} points at an unknown model constraint"
        assert expected_sql.strip(), f"{key} is mapped without the expected portable SQL"


# --- Comparator mechanism: each guard must actually detect drift -------------


def _mini_final(columns_sql: str, table: str = "demo") -> FinalSchema:
    return parse_final(f'CREATE TABLE "{table}" ({columns_sql})')


def _mini_models(*columns: sa.Column[object], table: str = "demo") -> dict[str, object]:
    metadata = sa.MetaData()
    sa.Table(table, metadata, *columns)
    return parse_models(metadata)


def test_comparator_detects_kind_mismatch() -> None:
    """uuid rendered as text must not pass as an equivalent column."""
    final = _mini_final('"code" uuid')
    models = _mini_models(sa.Column("code", sa.String(32)))
    gap = compare(final, models)  # type: ignore[arg-type]
    assert any("demo.code" in item for item in gap.details.get("kind", [])), gap.details


def test_comparator_detects_lost_unique() -> None:
    final = _mini_final('"code" varchar(32) UNIQUE')
    models = _mini_models(sa.Column("code", sa.String(32)))
    gap = compare(final, models)  # type: ignore[arg-type]
    assert gap.details.get("unique_missing") == ["demo['code']"], gap.details


def test_comparator_detects_default_value_mismatch() -> None:
    final = _mini_final('"flag" boolean DEFAULT true')
    models = _mini_models(sa.Column("flag", sa.Boolean, server_default=sa.text("0")))
    gap = compare(final, models)  # type: ignore[arg-type]
    assert gap.details.get("default_value"), gap.details


def test_allowlisted_tables_are_counted() -> None:
    """An allowlisted table must show up as counted debt, not vanish."""
    final = parse_final("")
    models = _mini_models(sa.Column("id", sa.Integer, primary_key=True), table="settings")
    gap = compare(final, models)  # type: ignore[arg-type]
    assert gap.details.get("allowlisted") == ["legacy:settings"], gap.details
    assert not gap.details.get("table_extra"), gap.details


def test_allowlists_are_documented() -> None:
    """Adding a name to an allowlist must also touch its decision record."""
    adr = (PROJECT_ROOT / "docs" / "adr" / "0028-sqlite-final-schema-alignment.md").read_text(
        encoding="utf-8"
    )
    matrix = (PROJECT_ROOT / "docs" / "SCHEMA-MIGRATION-MATRIX.md").read_text(encoding="utf-8")
    for name in ADR_EXTENSIONS:
        assert name in adr, f"{name} is allowlisted but absent from ADR-028"
    for name in LEGACY_RETENTION + NO_TARGET:
        assert name in matrix, f"{name} is allowlisted but absent from the schema matrix"


def test_dump_hash_matches_the_decision_record() -> None:
    """Relaxing the vendored dump must also update ADR-028, never silently."""
    adr = (PROJECT_ROOT / "docs" / "adr" / "0028-sqlite-final-schema-alignment.md").read_text(
        encoding="utf-8"
    )
    dump_hash = sha256_file(FINAL_DUMP)
    assert dump_hash in adr, (
        f"{dump_hash} is not recorded in ADR-028; a change to the final modeling "
        "needs an explicit decision update"
    )
