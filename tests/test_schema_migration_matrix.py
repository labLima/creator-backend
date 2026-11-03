from __future__ import annotations

import re
from pathlib import Path

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.schema_manifest import LEGACY_TABLES, PDF_TABLES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATRIX = PROJECT_ROOT / "docs" / "SCHEMA-MIGRATION-MATRIX.md"
BEHAVIOR_MATRIX = PROJECT_ROOT / "docs" / "migration" / "legacy-compatibility-matrix.md"
INVENTORY = PROJECT_ROOT / "docs" / "migration" / "legacy-inventory.md"


def _documented_table_names() -> set[str]:
    text = MATRIX.read_text(encoding="utf-8")
    candidates = set(re.findall(r"`([a-z][a-z0-9_]*)`", text))
    return candidates & set(Base.metadata.tables)


def test_schema_migration_matrix_covers_every_table() -> None:
    """The migration inventory must not silently omit a registered table."""
    documented = _documented_table_names()

    assert set(Base.metadata.tables) <= documented, sorted(set(Base.metadata.tables) - documented)


def test_schema_migration_matrix_covers_pdf_and_legacy_sets() -> None:
    documented = _documented_table_names()

    assert PDF_TABLES <= documented, sorted(PDF_TABLES - documented)
    assert LEGACY_TABLES <= documented, sorted(LEGACY_TABLES - documented)


def test_legacy_rows_have_category_status_target_action_and_evidence() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    rows = {
        match.group(1): match
        for match in re.finditer(
            r"^\| `([a-z][a-z0-9_]*)` \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
            text,
            flags=re.MULTILINE,
        )
    }
    for table in sorted(LEGACY_TABLES | {"auth_sessions", "outbox_events"}):
        assert table in rows, f"missing legacy row: {table}"
        assert all(cell.strip() for cell in rows[table].groups()[1:])


def test_behavior_matrix_counts_match_rows() -> None:
    rows = [
        line
        for line in BEHAVIOR_MATRIX.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| \d+ \|", line)
    ]
    counts = {"equivalente": 0, "parcial": 0, "ausente": 0, "novo/fora": 0}
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        status = cells[4].replace("*", "").strip().lower()
        if status == "equivalente":
            counts["equivalente"] += 1
        elif status == "parcial":
            counts["parcial"] += 1
        elif status == "ausente":
            counts["ausente"] += 1
        elif status in {"novo", "novo/fora", "fora de escopo"}:
            counts["novo/fora"] += 1
        else:
            raise AssertionError(f"unexpected status {cells[4]!r} in {row}")

    assert len(rows) == 32
    assert counts == {"equivalente": 0, "parcial": 20, "ausente": 9, "novo/fora": 3}


def test_legacy_behavior_inventory_exists() -> None:
    assert INVENTORY.is_file()
    assert BEHAVIOR_MATRIX.is_file()
    behavior = BEHAVIOR_MATRIX.read_text(encoding="utf-8")
    assert "Equivalente" in behavior
    assert "Parcial" in behavior
    assert "Ausente" in behavior
