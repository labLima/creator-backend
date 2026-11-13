"""T16 (issue #164): ADR-031 must record the retirement, its reasons and its deadlines.

ADR-030 finished the schema alignment but left two decisions open: the eleven
legacy tables and the two tables without a target in ``Creator_DB_final.sql``
(``provider_customers`` and ``provider_subscriptions``). ADR-031 closes them. A
decision that only exists in a migration is invisible to the next reader, so this
module asserts the three documents that carry it:

- ``docs/adr/0031-legacy-table-retirement.md`` classifies every one of the 13
  tables, with a retention deadline for the ones that stay and a removal verdict
  for the ones that go;
- ``docs/SCHEMA-MIGRATION-MATRIX.md`` reflects the retirement and the retention
  deadlines instead of still presenting both provider tables as final-model tables;
- ``docs/ADR-ISSUE-TRACKER.md`` links ADR-031 to issue #164, so the decision keeps
  one tracker issue as AGENTS.md requires.

The assertions read the documents as text on purpose: they are the artefact under
test, and a formatting-independent check (table row, marker word, link) is what
makes a missing classification fail instead of an unlucky line break.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADR = PROJECT_ROOT / "docs" / "adr" / "0031-legacy-table-retirement.md"
ADR_030 = PROJECT_ROOT / "docs" / "adr" / "0030-sqlite-final-schema-alignment.md"
MATRIX = PROJECT_ROOT / "docs" / "SCHEMA-MIGRATION-MATRIX.md"
TRACKER = PROJECT_ROOT / "docs" / "ADR-ISSUE-TRACKER.md"

# The 13 tables ADR-030 handed to T16: 11 legacy retentions and 2 without a target.
LEGACY_TABLES = (
    "agent_workflow_runs",
    "agent_workflow_steps",
    "assets",
    "brand_settings",
    "contents",
    "generation_job_status_events",
    "generation_jobs",
    "generations",
    "images",
    "projects",
    "settings",
)
RETIRED_PROVIDER_TABLES = ("provider_customers", "provider_subscriptions")

# A retention needs a deadline, not a promise: a date, a target task or an explicit
# "prazo"/"deadline" marker in the same row. The matrix already uses
# `(2026-11-04)` as evidence that a legacy migration is not planned; that date is
# history, not a deadline, so it never counts.
DEADLINE_MARKERS = ("prazo", "deadline")
DEADLINE_PATTERN = re.compile(r"\b20\d\d-\d\d-\d\d\b")
TASK_PATTERN = re.compile(r"\bT\d{2}\b")
HISTORICAL_EVIDENCE_DATE = "2026-11-04"


def _text(path: Path) -> str:
    assert path.is_file(), f"{path.relative_to(PROJECT_ROOT)} is missing"
    return path.read_text(encoding="utf-8")


def _rows(text: str, table: str) -> list[str]:
    """Markdown table rows that name `table` in their first cell."""
    pattern = re.compile(r"^\| `" + re.escape(table) + r"` \|(.*)$", re.MULTILINE)
    return [match.group(0) for match in pattern.finditer(text)]


def _has_deadline(row: str) -> bool:
    lowered = row.lower()
    if any(marker in lowered for marker in DEADLINE_MARKERS):
        return True
    if TASK_PATTERN.search(row):
        return True
    return any(date != HISTORICAL_EVIDENCE_DATE for date in DEADLINE_PATTERN.findall(row))


# --- ADR-031 exists, is numbered 0031 and classifies every table -------------


def test_adr_031_exists_and_is_numbered_0031() -> None:
    """The retirement ADR is 0031; 0029 and 0030 are already taken."""
    text = _text(ADR)
    heading = next((line for line in text.splitlines() if line.startswith("# ")), "")

    assert re.match(r"^#\s+ADR-031\b", heading), (
        f"docs/adr/0031-legacy-table-retirement.md must start with `# ADR-031 ...`, got {heading!r}"
    )
    assert not re.search(r"^#\s+ADR-0(29|30)\b", text, flags=re.MULTILINE), (
        "the retirement ADR reuses the number of an existing decision (ADR-029 image review, "
        "ADR-030 schema alignment)"
    )


@pytest.mark.parametrize("table", LEGACY_TABLES + RETIRED_PROVIDER_TABLES)
def test_adr_031_classifies_every_table_of_the_t16_scope(table: str) -> None:
    """No table may be missing a classification row."""
    rows = _rows(_text(ADR), table)

    assert rows, (
        f"ADR-031 has no classification row for `{table}`; the decision must name the "
        "destination of all 11 legacy tables and both provider tables"
    )


@pytest.mark.parametrize("table", LEGACY_TABLES)
def test_adr_031_records_a_retention_deadline_for_each_legacy_table(table: str) -> None:
    """A retained table without a deadline is an undecided table (T16 acceptance)."""
    rows = _rows(_text(ADR), table)

    assert rows, f"ADR-031 does not classify `{table}`"
    with_deadline = [row for row in rows if _has_deadline(row)]
    assert with_deadline, (
        f"the ADR-031 row for the retained legacy table `{table}` carries no retention "
        f"deadline (a date, a target task such as `T23`, or the word `prazo`): {rows}"
    )


@pytest.mark.parametrize("table", RETIRED_PROVIDER_TABLES)
def test_adr_031_records_the_removal_of_the_provider_cache_tables(table: str) -> None:
    """The two no-target tables are removed, not retained."""
    rows = _rows(_text(ADR), table)

    assert rows, f"ADR-031 does not classify `{table}`"
    removed = [
        row
        for row in rows
        if re.search(r"remov|aposent|drop|retirad|sem alvo", row, flags=re.IGNORECASE)
    ]
    assert removed, (
        f"ADR-031 must record that `{table}` is removed: the final modeling has no "
        f"provider customer/subscription cache. Row(s): {rows}"
    )


def test_adr_031_declares_the_brands_extension_as_permanent() -> None:
    """`brands(id, workspace_id)` stays by decision, not by leftover debt."""
    text = _text(ADR)
    rows = _rows(text, "brands")
    candidates = rows or [line for line in text.splitlines() if "brands" in line]

    assert candidates, "ADR-031 does not mention the brands extension"
    accepted = [
        line
        for line in candidates
        if "workspace_id" in line
        and re.search(r"permanent|permanente|extens", line, flags=re.IGNORECASE)
    ]
    assert accepted, (
        "ADR-031 must declare `brands(id, workspace_id)` a permanent extension of the final "
        f"modeling; rows mentioning brands: {candidates}"
    )


def test_adr_031_records_the_downgrade_data_loss() -> None:
    """A contract downgrade recreates structure only; the ADR has to say so."""
    text = _text(ADR).lower()

    assert "downgrade" in text, "ADR-031 does not mention the downgrade"
    assert "dados" in text or "data" in text, (
        "ADR-031 must state what the downgrade does with the dropped rows"
    )
    assert re.search(r"perda|loss|não .*restaur|nao .*restaur|backup", text), (
        "ADR-031 must document that the retirement loses the provider cache rows and that "
        "recovery depends on a backup"
    )


# --- ADR-030 hands the decision over with a link -----------------------------


def test_adr_030_links_the_retirement_adr() -> None:
    """ADR-030 says the two tables are 'decided in ADR-031'; the link must resolve."""
    text = _text(ADR_030)

    assert "0031-legacy-table-retirement.md" in text, (
        "ADR-030 hands the provider tables to ADR-031; it must link "
        "`0031-legacy-table-retirement.md` instead of leaving a dangling reference"
    )


# --- the migration matrix reflects the retirement ----------------------------


def test_schema_matrix_no_longer_lists_the_provider_tables_as_final_model_tables() -> None:
    """Both tables are absent from the dump; the matrix must stop claiming otherwise."""
    text = _text(MATRIX)
    final_section = text.split("## Tabelas nativas do PDF", 1)
    native = final_section[1].split("\n## ", 1)[0] if len(final_section) == 2 else ""

    for table in RETIRED_PROVIDER_TABLES:
        assert f"- `{table}`" not in native, (
            f"docs/SCHEMA-MIGRATION-MATRIX.md still lists `{table}` as a native table of the "
            "final modeling; the dump never declared it and ADR-031 retires it"
        )
        rows = _rows(text, table)
        assert rows, f"the matrix dropped `{table}` without recording the retirement"
        retired = [
            row
            for row in rows
            if re.search(r"retirad|removid|aposent|ADR-031", row, flags=re.IGNORECASE)
        ]
        assert retired, (
            f"the matrix row for `{table}` must record the retirement (link ADR-031 or say "
            f"the table was removed); got {rows}"
        )


@pytest.mark.parametrize("table", LEGACY_TABLES)
def test_schema_matrix_records_a_retention_deadline_for_each_legacy_table(table: str) -> None:
    """The matrix is the per-table inventory: retention needs its deadline there too."""
    rows = _rows(_text(MATRIX), table)

    assert rows, f"docs/SCHEMA-MIGRATION-MATRIX.md has no row for `{table}`"
    with_deadline = [row for row in rows if _has_deadline(row)]
    assert with_deadline, (
        f"the matrix row for the retained legacy table `{table}` still has no retention "
        f"deadline: {rows}"
    )


def test_schema_matrix_counts_follow_the_retirement() -> None:
    """71 tables minus the two retired ones is 69; 13 legacy/no-target becomes 11."""
    text = _text(MATRIX)
    header = "\n".join(text.splitlines()[:8])

    assert "69 tabelas" in header, (
        "the matrix header still counts the tables of the pre-T16 metadata; after ADR-031 the "
        f"metadata has 69 tables. Header: {header!r}"
    )
    assert "11 legadas" in header, (
        f"the matrix header must count 11 legacy tables after the retirement. Header: {header!r}"
    )
    assert "13 legadas" not in header, (
        "the matrix header still counts 13 legacy/no-target tables, which includes the two "
        "retired provider tables"
    )


# --- the ADR tracker keeps one issue per decision ----------------------------


def test_tracker_links_adr_031_to_issue_164() -> None:
    """AGENTS.md: every ADR has one tracker issue; T16 is #164."""
    rows = [line for line in _text(TRACKER).splitlines() if line.startswith("| [ADR-031]")]

    assert rows, "docs/ADR-ISSUE-TRACKER.md has no row for ADR-031"
    assert any(
        "0031-legacy-table-retirement.md" in row and re.search(r"\b164\b", row) and "0060" in row
        for row in rows
    ), (
        "the ADR-031 tracker row must link `0031-legacy-table-retirement.md`, issue #164 and "
        f"the SQLite alignment epic; got {rows}"
    )
