"""Regenerate ``tests/contracts/serializers.json`` from the contract helper.

The characterization test in ``tests/test_serializer_contract.py`` owns the
single implementation of the snapshot: it defines the fixture record and the
mapper list it asserts against. This module only writes that output, so the
snapshot cannot drift from the test that guards it.

Usage:
    python -m tests.snapshot_serializers
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_serializer_contract import build_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = PROJECT_ROOT / "tests" / "contracts" / "serializers.json"


def main() -> int:
    snapshot = build_snapshot()
    SNAPSHOT.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"serializers.json: {len(snapshot)} mappers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
