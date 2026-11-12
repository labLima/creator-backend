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

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

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
    ModelColumn,
    ModelTable,
    compare,
    gap_counts,
    gap_digest,
    model_kind,
    normalize_kind,
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
    # Cross-cutting decision ledger: it aggregates enum CHECKs, ADR-020 columns and
    # the captions predicate, so it belongs to no single comparison dimension. Filing
    # it under `checks` would claim a CHECK-only guarantee that 4 of its items (2
    # columns, 2 indexes) do not provide.
    "declared_exceptions": ("declared_exception",),
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
    adr = (PROJECT_ROOT / "docs" / "adr" / "0029-sqlite-final-schema-alignment.md").read_text(
        encoding="utf-8"
    )
    matrix = (PROJECT_ROOT / "docs" / "SCHEMA-MIGRATION-MATRIX.md").read_text(encoding="utf-8")
    for name in ADR_EXTENSIONS:
        assert name in adr, f"{name} is allowlisted but absent from ADR-029"
    for name in LEGACY_RETENTION + NO_TARGET:
        assert name in matrix, f"{name} is allowlisted but absent from the schema matrix"


def test_dump_hash_matches_the_decision_record() -> None:
    """Relaxing the vendored dump must also update ADR-029, never silently."""
    adr = (PROJECT_ROOT / "docs" / "adr" / "0029-sqlite-final-schema-alignment.md").read_text(
        encoding="utf-8"
    )
    dump_hash = sha256_file(FINAL_DUMP)
    assert dump_hash in adr, (
        f"{dump_hash} is not recorded in ADR-029; a change to the final modeling "
        "needs an explicit decision update"
    )


# --- T26: declared exceptions, kind classifier and report coverage -----------
#
# Three families of divergence are decisions, not debt: the CHECK constraints that
# SQLAlchemy generates for enum columns, the ADR-020 authentication columns that the
# final modeling does not carry, and the one dump inconsistency recorded in ADR-029
# (`uq_captions_current` filters `deleted_at`, a column `captions` does not have).
# They move to a `declared_exception` category so `Gap.unexpected_total()` — the
# number the `--check` gate uses — stops counting them as drift.


def test_normalize_kind_prefers_enum_vocabulary_over_char_prefix() -> None:
    """`charge_status` starts with "char"; the enum vocabulary must win.

    The dump declares `charges.status` as `charge_status`. The `char` prefix branch
    runs first today, so the column is classified as `varchar` and reported as a
    kind mismatch even though both sides agree on the vocabulary.
    """
    assert normalize_kind("charge_status", frozenset({"charge_status"})) == "enum"


def test_normalize_kind_still_collapses_char_types() -> None:
    """The enum fix must not turn real character types into enums."""
    assert normalize_kind("char(2)", frozenset({"charge_status"})) == "varchar(2)"
    assert normalize_kind("character varying(254)", frozenset({"charge_status"})) == "varchar(254)"
    assert normalize_kind("char", frozenset({"charge_status"})) == "varchar"


def test_model_kind_maps_date_columns_to_date() -> None:
    """`sa.Date` is a first-class kind: the dump declares real `date` columns.

    Without a branch, `model_kind` returns `"other"` and every date column shows up
    as a kind mismatch instead of matching the dump.
    """
    assert model_kind(sa.Date()) == ("date", None, None)


def test_model_kind_keeps_datetime_as_timestamp() -> None:
    """Adding `date` must not shadow the timestamp classification."""
    assert model_kind(sa.DateTime()) == ("timestamp", None, None)
    assert model_kind(sa.DateTime(timezone=True)) == ("timestamp", None, None)


def test_gap_categories_include_declared_exception() -> None:
    """Declared exceptions need their own budgeted category, not an allowlist."""
    assert "declared_exception" in GAP_CATEGORIES


def test_declared_exception_counts_as_a_category() -> None:
    gap = Gap(details={"declared_exception": ["enum-check:demo.status"]})
    assert gap.counts()["declared_exception"] == 1


def test_unexpected_total_excludes_allowlisted_and_declared_exceptions() -> None:
    """`unexpected_total` is what the `--check` gate must compare against zero."""
    gap = Gap(
        details={
            "allowlisted": ["adr_extension:auth_sessions", "legacy:settings"],
            "declared_exception": [
                "enum-check:users.global_role",
                "adr-020:users.password_hash",
                "dump-inconsistency:captions: predicate is_current",
            ],
            "kind": ["demo.code: final uuid, model text"],
        }
    )

    assert gap.total() == 6, "allowlisted and declared items are still part of the raw total"
    assert gap.unexpected_total() == 1, (
        "only items outside allowlisted and declared_exception are unexpected"
    )


def _expected_enum_checks() -> set[str]:
    """Model CHECKs that exist only because an enum column generated them.

    Restricted to the 54 tables of the final modeling: the legacy and allowlisted
    tables are not compared, so their checks are not part of the declared set.
    """
    final_tables = set(_final().tables)
    expected: set[str] = set()
    for table in Base.metadata.tables.values():
        if table.name not in final_tables:
            continue
        for column in table.columns:
            column_type = column.type
            if (
                isinstance(column_type, sa.Enum)
                and column_type.create_constraint
                and column_type.name
            ):
                expected.add(f"enum-check:{table.name}.{column_type.name}")
    return expected


def test_enum_generated_checks_are_declared_exceptions() -> None:
    """Enum CHECKs are generated by `create_constraint=True`, not schema debt."""
    expected = _expected_enum_checks()
    assert len(expected) == 30, sorted(expected)

    declared = set(_gap().details.get("declared_exception", []))
    assert expected <= declared, sorted(expected - declared)
    assert "enum-check:users.global_role" in declared
    assert not _gap().details.get("check_extra"), (
        "enum-generated checks must not remain in check_extra"
    )


def test_adr_020_columns_are_declared_exceptions() -> None:
    """ADR-020 requires local credentials the final modeling does not carry."""
    gap = _gap()
    declared = [
        item for item in gap.details.get("declared_exception", []) if item.startswith("adr-020:")
    ]

    assert sorted(declared) == ["adr-020:users.global_role", "adr-020:users.password_hash"], (
        declared
    )
    extra = gap.details.get("column_extra", [])
    assert "users.password_hash" not in extra
    assert "users.global_role" not in extra


def test_captions_partial_index_is_a_declared_dump_inconsistency() -> None:
    """ADR-029 records that the dump filters a column `captions` does not have.

    Both halves of the predicate mismatch are declared: the dump index is missing
    and the metadata index is extra. Neither is retried as ordinary index debt.
    """
    gap = _gap()
    dump_items = [
        item
        for item in gap.details.get("declared_exception", [])
        if item.startswith("dump-inconsistency:")
    ]

    assert len(dump_items) == 2, dump_items
    assert all("captions" in item for item in dump_items), dump_items
    assert all("is_current" in item for item in dump_items), dump_items
    assert any("deleted_at" in item for item in dump_items), dump_items
    assert not [item for item in gap.details.get("index_missing", []) if "captions" in item]
    assert not [item for item in gap.details.get("index_extra", []) if "captions" in item]


def test_declared_exceptions_cover_exactly_the_three_families() -> None:
    """The declared set is enumerable: nothing arrives in it by accident."""
    declared = _gap().details.get("declared_exception", [])
    families = Counter(item.partition(":")[0] for item in declared)

    assert set(families) == {"enum-check", "adr-020", "dump-inconsistency"}, families
    assert families["enum-check"] == len(_expected_enum_checks())
    assert families["adr-020"] == 2
    assert families["dump-inconsistency"] == 2


def test_declared_exceptions_leave_only_credit_ledger_debt() -> None:
    """Everything the declaration absorbs must disappear from its old category."""
    gap = _gap()
    counts = gap_counts(gap)

    assert counts["kind"] == 0, gap.details.get("kind")
    assert counts["check_extra"] == 0, gap.details.get("check_extra")
    assert counts["index_extra"] == 0, gap.details.get("index_extra")

    columns = gap.details.get("column_extra", [])
    assert columns, "the credit ledger still owes column work; the whole list cannot be empty"
    assert all(item.startswith("workspace_credit_transactions.") for item in columns), columns

    indexes = gap.details.get("index_missing", [])
    assert indexes, "the credit ledger still owes index work; the whole list cannot be empty"
    assert all(item.startswith("workspace_credit_transactions:") for item in indexes), indexes


def test_unexpected_total_on_the_real_gap_ignores_declared_and_allowlisted() -> None:
    """The gate number is the debt minus both decisions, not the raw total."""
    gap = _gap()
    counts = gap_counts(gap)

    assert counts["declared_exception"] > 0
    assert gap.unexpected_total() == (
        gap.total() - counts["allowlisted"] - counts["declared_exception"]
    )
    assert gap.unexpected_total() > 0, "the remaining debt is real and must stay visible"


def _load_report_script() -> ModuleType:
    """Load the report script by path: ``scripts/`` and ``tests/`` never import."""
    path = PROJECT_ROOT / "scripts" / "schema_parity_report.py"
    spec = importlib.util.spec_from_file_location("creator_schema_parity_report_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


KIND_ITEM = "demo.code: final uuid, model text"
UNIQUE_MISSING_ITEM = "demo['code']"
UNIQUE_EXTRA_ITEM = "demo['code', 'workspace_id']"


def test_report_renders_kind_and_unique_categories() -> None:
    """The report must show every compared dimension, not only the ones with zero."""
    module = _load_report_script()
    gap = Gap(
        details={
            "kind": [KIND_ITEM],
            "unique_missing": [UNIQUE_MISSING_ITEM],
            "unique_extra": [UNIQUE_EXTRA_ITEM],
        }
    )

    rendered = module.render(parse_final(""), gap, "sha256:test", 0)

    for category, item in (
        ("kind", KIND_ITEM),
        ("unique_missing", UNIQUE_MISSING_ITEM),
        ("unique_extra", UNIQUE_EXTRA_ITEM),
    ):
        assert f"- `{item}`" in rendered, f"{category} item missing from the report"
        assert rendered.count(f"`{category}`") >= 2, (
            f"{category} needs a labelled section: the label appears only in the "
            "summary table, so the items are not rendered"
        )


def test_check_flag_accepts_allowlisted_and_declared_exceptions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`--check` must compare `unexpected_total()`, never the raw total."""
    module = _load_report_script()
    report = tmp_path / "schema-final-alignment.md"
    monkeypatch.setattr(module, "REPORT", report)
    tolerated = Gap(
        details={
            "allowlisted": ["adr_extension:auth_sessions", "legacy:settings"],
            "declared_exception": [
                "enum-check:users.global_role",
                "adr-020:users.password_hash",
                "dump-inconsistency:captions: predicate is_current",
            ],
        }
    )
    monkeypatch.setattr(module, "compare", lambda final, models: tolerated)

    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py"])
    assert module.main() == 0, "a normal run must succeed"
    assert report.exists(), "a normal run must write the report"
    fresh = report.read_text(encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py", "--check"])
    assert module.main() == 0, (
        "--check failed on allowlisted and declared items; the exit code must come "
        "from Gap.unexpected_total() with an up-to-date report"
    )
    assert report.read_text(encoding="utf-8") == fresh, "--check must not rewrite the report"


def test_check_flag_still_fails_on_unexpected_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Relaxing the gate must not make real drift pass."""
    module = _load_report_script()
    report = tmp_path / "schema-final-alignment.md"
    monkeypatch.setattr(module, "REPORT", report)
    monkeypatch.setattr(module, "compare", lambda final, models: Gap(details={"kind": [KIND_ITEM]}))

    # A fresh report isolates the exit code from the staleness check.
    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py"])
    assert module.main() == 0

    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py", "--check"])
    assert module.main() == 1


# --- T26 review follow-up: explicit index allowlist, enum SQL semantics, -----
# --- read-only `--check` and enum defaults -----------------------------------


def test_normal_run_writes_the_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Writing stays the default behaviour; only `--check` becomes read-only."""
    module = _load_report_script()
    report = tmp_path / "schema-final-alignment.md"
    monkeypatch.setattr(module, "REPORT", report)
    monkeypatch.setattr(module, "compare", lambda final, models: Gap(details={}))
    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py"])

    assert module.main() == 0

    written = report.read_text(encoding="utf-8")
    assert written.startswith("# Alinhamento ao Creator_DB_final.sql"), written[:120]


def test_check_flag_is_read_only_and_fails_on_a_stale_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--check` is a gate: no write, and an outdated report must fail it."""
    module = _load_report_script()
    report = tmp_path / "schema-final-alignment.md"
    stale = "# relatório antigo\n"
    report.write_text(stale, encoding="utf-8")
    monkeypatch.setattr(module, "REPORT", report)
    monkeypatch.setattr(module, "compare", lambda final, models: Gap(details={}))
    monkeypatch.setattr(sys, "argv", ["schema_parity_report.py", "--check"])

    assert module.main() == 1, "an out-of-date report must fail the gate"
    assert report.read_text(encoding="utf-8") == stale, "--check must never write the report"

    captured = capsys.readouterr()
    assert "stale" in (captured.out + captured.err).lower(), (
        "the failure must name the stale report, got "
        f"stdout={captured.out!r} stderr={captured.err!r}"
    )


# --- T26 review follow-up: explicit index allowlist and enum SQL semantics ---


def test_dump_index_inconsistencies_is_an_explicit_allowlist() -> None:
    """The dump inconsistency lives in one declared map, not in a heuristic."""
    from creator.infrastructure.database import final_schema as module

    allowlist = getattr(module, "DUMP_INDEX_INCONSISTENCIES", None)
    assert isinstance(allowlist, dict), (
        "final_schema must declare DUMP_INDEX_INCONSISTENCIES: dict[tuple[str, str], str] "
        "keyed by (table, index_name)"
    )
    assert set(allowlist) == {("captions", "uq_captions_current")}, sorted(allowlist)
    for key, reason in allowlist.items():
        assert isinstance(key, tuple) and len(key) == 2, key
        assert isinstance(reason, str) and reason.strip(), f"{key} needs a written reason"


def test_predicate_with_function_identifier_stays_index_debt() -> None:
    """Only the allowlisted index may be declared; a predicate shape is not enough."""
    final = parse_final(
        'CREATE TABLE "demo" ("id" integer, "status" varchar(8));\n'
        'CREATE INDEX "uq_demo_status" ON "demo" ("status") WHERE lower(status) = \'x\''
    )
    metadata = sa.MetaData()
    table = sa.Table(
        "demo",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(8)),
    )
    sa.Index("uq_demo_status", table.c.status, unique=True, sqlite_where=sa.text("status = 'x'"))
    models = parse_models(metadata)

    gap = compare(final, models)

    declared = [item for item in gap.details.get("declared_exception", []) if "demo" in item]
    assert not declared, (
        "a predicate containing a function identifier is not an allowlisted dump "
        f"inconsistency and must stay index debt: {declared}"
    )
    assert [item for item in gap.details.get("index_missing", []) if "demo" in item], gap.details
    assert [item for item in gap.details.get("index_extra", []) if "demo" in item], gap.details


def _enum_final() -> FinalSchema:
    return parse_final(
        "CREATE TYPE \"demo_status\" AS ENUM ('a', 'b');\n"
        'CREATE TABLE "demo" ("status" demo_status)'
    )


def _enum_model_table(*, check_sql: str, expected_sql: str) -> ModelTable:
    return ModelTable(
        name="demo",
        columns={
            "status": ModelColumn(
                name="status",
                nullable=True,
                primary_key=False,
                kind="enum",
                length=None,
                enum_values=("a", "b"),
                unique=False,
                has_default=False,
                default_text=None,
            )
        },
        indexes=(),
        foreign_keys=(),
        checks=(("status", check_sql),),
        uniques=(),
        enum_checks=(("status", expected_sql),),
    )


def test_enum_checks_are_check_name_and_normalized_sql_pairs() -> None:
    """`enum_checks` must carry the vocabulary SQL, not only the constraint name."""
    pairs = parse_models(Base.metadata)["brand_assets"].enum_checks

    assert isinstance(pairs, tuple) and pairs, (
        f"brand_assets declares an enum column with create_constraint, got {pairs!r}"
    )
    for entry in pairs:
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"enum_checks must hold (check_name, normalized_sql) pairs, got {entry!r}"
        )
        check_name, normalized_sql = entry
        assert isinstance(check_name, str) and isinstance(normalized_sql, str), entry
    vocabulary_sql = dict(pairs)["brand_asset_type"]
    literals = {literal.lower() for literal in re.findall(r"'([^']*)'", vocabulary_sql)}
    assert literals == {"logo", "image", "font", "icon", "document", "other"}, (
        "the pair must encode the brand_asset_type vocabulary exactly; got "
        f"{sorted(literals)} in {vocabulary_sql!r}"
    )
    assert "text" not in literals, (
        "brand_asset_type has no TEXT member, so no canonical check may require one; "
        f"got {vocabulary_sql!r}"
    )


def test_enum_check_with_different_sql_stays_check_extra() -> None:
    """The exemption must verify the SQL, not only the constraint name."""
    model = _enum_model_table(check_sql="status in ('x')", expected_sql="status in ('a', 'b')")

    gap = compare(_enum_final(), {"demo": model})

    assert gap.details.get("check_extra") == ["demo.status"], gap.details
    assert not gap.details.get("declared_exception"), gap.details


def test_enum_check_with_matching_sql_is_declared() -> None:
    """A check that really encodes the vocabulary stays a declared exception."""
    model = _enum_model_table(
        check_sql="status in ('a', 'b')",
        expected_sql="status in ('a', 'b')",
    )

    gap = compare(_enum_final(), {"demo": model})

    assert gap.details.get("declared_exception") == ["enum-check:demo.status"], gap.details
    assert not gap.details.get("check_extra"), gap.details


def test_enum_checks_ignore_a_colliding_hand_written_check() -> None:
    """`enum_checks` must come from the enum column, never from the CHECK list.

    A hand-written CHECK may reuse an enum's name. If the expected vocabulary SQL is
    read back from the model checks, that predicate becomes the expectation: the
    hand-written rule is silently declared and the genuine enum check turns into
    debt.
    """
    metadata = sa.MetaData()
    table = sa.Table(
        "demo",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "status",
            sa.Enum("a", "b", name="demo_status", native_enum=False, create_constraint=True),
        ),
    )
    hand_written = "length(status) between 1 and 9"
    table.append_constraint(sa.CheckConstraint(hand_written, name="demo_status"))

    models = parse_models(metadata)

    pairs = models["demo"].enum_checks
    assert pairs == (("demo_status", "demo.status in ('a', 'b')"),), (
        "enum_checks must be derived from column.type.enums only: exactly one pair in "
        f"the plain IN form for demo_status, got {pairs!r}"
    )
    expected_sql = pairs[0][1]
    assert "cast(" not in expected_sql, (
        f"the canonical enum SQL must not need a cast, got {expected_sql!r}"
    )

    check_sqls = [sql for _name, sql in models["demo"].checks]
    assert hand_written in check_sqls, check_sqls
    assert not [sql for sql in check_sqls if "cast(" in sql], (
        f"the real enum constraint SQL must stay in checks instead of a cast rewrite: {check_sqls}"
    )

    gap = compare(_enum_final(), models)

    assert gap.details.get("declared_exception") == ["enum-check:demo.demo_status"], gap.details
    assert gap.details.get("check_extra") == ["demo.demo_status"], (
        "the hand-written CHECK must stay visible as check_extra instead of being "
        f"swallowed by the enum exemption: {gap.details}"
    )


# --- T26 review follow-up: defaults are compared for enum columns too --------

ENUM_DUMP_WITH_DEFAULT = (
    "CREATE TYPE \"demo_status\" AS ENUM ('a', 'b');\n"
    'CREATE TABLE "demo" ("id" integer, "status" demo_status DEFAULT \'a\')'
)


def _enum_status_column(**kwargs: object) -> sa.Column[str]:
    return sa.Column(
        "status",
        sa.Enum("a", "b", name="demo_status", native_enum=False, create_constraint=True),
        **kwargs,  # type: ignore[arg-type]
    )


def test_enum_column_without_model_default_reports_default_missing() -> None:
    """The enum vocabulary branch must not skip the default comparison."""
    final = parse_final(ENUM_DUMP_WITH_DEFAULT)
    models = _mini_models(
        sa.Column("id", sa.Integer, primary_key=True),
        _enum_status_column(),
    )

    gap = compare(final, models)  # type: ignore[arg-type]

    missing = gap.details.get("default_missing", [])
    assert any(item.startswith("demo.status") for item in missing), (
        f"the enum default is not compared at all: {missing}"
    )


def test_enum_column_with_matching_default_is_not_reported() -> None:
    """Adding the default comparison must not invent debt when defaults agree."""
    final = parse_final(ENUM_DUMP_WITH_DEFAULT)
    models = _mini_models(
        sa.Column("id", sa.Integer, primary_key=True),
        _enum_status_column(server_default=sa.text("'a'")),
    )

    gap = compare(final, models)  # type: ignore[arg-type]

    assert not gap.details.get("default_missing"), gap.details
    assert not gap.details.get("default_value"), gap.details
