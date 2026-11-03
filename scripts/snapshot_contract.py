"""Freeze the observable HTTP and persistence contract as reviewable snapshots.

The refactor moves code between modules without changing behavior. These
snapshots make "nothing changed" a machine-checked fact instead of a review
opinion. Running this script rewrites the snapshots; commit the diff only when
the contract change is intentional and reviewed.

Usage:
    python scripts/snapshot_contract.py
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from creator.infrastructure.database.db import Base
from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def route_table() -> list[dict[str, object]]:
    """Return every documented operation with its observable metadata."""
    document = app.openapi()
    rows = [
        {
            "method": method.upper(),
            "path": path,
            "operation_id": operation["operationId"],
            "tags": list(operation.get("tags", [])),
        }
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]
    rows.sort(key=lambda row: (row["path"], row["method"]))
    return rows


def schema_ddl() -> str:
    """Return deterministic DDL for every registered table.

    Sorted by table name, not by dependency: the topological order of
    `sorted_tables` depends on model import order, which is exactly what this
    refactor changes. The snapshot must not care.
    """
    configure_mappers()
    dialect = sa.dialects.sqlite.dialect()
    statements = [
        str(CreateTable(table).compile(dialect=dialect)).strip()
        for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name)
    ]
    return "\n\n".join(statements) + "\n"


def registered_tables() -> list[str]:
    return sorted(Base.metadata.tables)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    rows = route_table()
    write_json(CONTRACTS / "route_table.json", rows)
    write_json(CONTRACTS / "schema_tables.json", registered_tables())
    (CONTRACTS / "schema_ddl.sql").write_text(schema_ddl(), encoding="utf-8")
    print(f"route_table.json: {len(rows)} operations")
    print(f"schema_tables.json: {len(registered_tables())} tables")


if __name__ == "__main__":
    main()
