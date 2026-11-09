"""Freeze the observable HTTP and persistence contract as reviewable snapshots.

The snapshots make "nothing changed" a machine-checked fact instead of a review
opinion. Running this script rewrites them; commit the diff only when the
contract change is intentional and reviewed.

``--check`` compares without writing and exits non-zero on any difference, so
``make check`` fails when a schema change ships without regenerating the
snapshots. The DDL snapshot includes tables **and** indexes: without indexes a
change that only touches an index would be invisible.

Usage:
    python scripts/snapshot_contract.py            # rewrite the snapshots
    python scripts/snapshot_contract.py --check    # fail on any drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.orm import configure_mappers

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.final_schema import render_schema_ddl
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
    """Return deterministic DDL for every registered table and index."""
    configure_mappers()
    return render_schema_ddl(Base.metadata, include_indexes=True)


def registered_tables() -> list[str]:
    return sorted(Base.metadata.tables)


def generate() -> dict[Path, str]:
    """Return the expected contents of every snapshot file."""
    rows = route_table()
    return {
        CONTRACTS / "route_table.json": json.dumps(rows, indent=2) + "\n",
        CONTRACTS / "schema_tables.json": json.dumps(registered_tables(), indent=2) + "\n",
        CONTRACTS / "schema_ddl.sql": schema_ddl(),
    }


def check() -> int:
    """Compare the snapshots with the live contract without writing."""
    failures: list[str] = []
    for path, expected in generate().items():
        actual = path.read_bytes() if path.exists() else b""
        if actual != expected.encode("utf-8"):
            failures.append(str(path.relative_to(PROJECT_ROOT)))
    if failures:
        for name in failures:
            print(f"snapshot drift: {name}", file=sys.stderr)
        print(
            "Run `make snapshot-contract` and review the diff in the same PR.",
            file=sys.stderr,
        )
        return 1
    print("snapshots are up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write; fail on drift")
    args = parser.parse_args()
    if args.check:
        return check()

    CONTRACTS.mkdir(parents=True, exist_ok=True)
    for path, content in generate().items():
        path.write_bytes(content.encode("utf-8"))
    print(f"route_table.json: {len(route_table())} operations")
    print(f"schema_tables.json: {len(registered_tables())} tables")
    print(f"schema_ddl.sql: {len(schema_ddl().splitlines())} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
