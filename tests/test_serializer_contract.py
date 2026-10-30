"""Golden-master guard for the response mappers.

These mappers are implementation, not public API, so this is deliberately a
characterization test: it proves that moving them between modules does not
change a single byte of the payload. The oracle is the pre-refactor behavior,
captured in `tests/contracts/serializers.json`; the guarantee that the payload
is *correct* comes from `tests/test_api.py` and the e2e suite, which assert
real HTTP responses.

Regenerate only when a payload change is intentional and reviewed:
    python -m tests.snapshot_serializers
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

import creator.api.serializers as main_module

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
SNAPSHOT = CONTRACTS / "serializers.json"

# Mappers with a different arity than the single-record form.
CUSTOM_ARITY = {
    "_content_detail_data",
    "_content_page_data",
    "_image_generation_status_data",
    "_page_data",
}


class FullRecord:
    """Record whose attributes exercise every branch of the mappers."""

    def __getattr__(self, name: str) -> object:
        if name in {"status", "human_review", "role", "type", "channel", "provider"}:
            return EnumValue()
        if name.endswith("_at") or name.endswith("_period"):
            return datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
        if name.endswith("_id") or name == "id":
            return UUID("11111111-1111-1111-1111-111111111111")
        if name in {"metadata", "payload", "objectives", "info", "price_brackets"}:
            return {"fixture": True}
        if name in {"is_active", "is_enabled", "closed", "delinquent", "signature_verified"}:
            return True
        if name in {"amount", "amount_cents", "price_cents", "quantity", "cycles", "attempts"}:
            return 1
        return f"fixture-{name}"


class EnumValue(str):
    """Behaves like a `StrEnum`: JSON-serializable and exposes `.value`."""

    def __new__(cls) -> EnumValue:
        return super().__new__(cls, "fixture")

    @property
    def value(self) -> str:
        return "fixture"


FIXTURES = {"full": FullRecord}


def mapper_names() -> list[str]:
    return sorted(
        name
        for name in dir(main_module)
        if name.startswith("_") and name.endswith("_data") and name not in CUSTOM_ARITY
    )


def render(mapper: Any, record: Any) -> str:
    return json.dumps(mapper(record), sort_keys=True, default=str)


def build_snapshot() -> dict[str, dict[str, str]]:
    return {
        name: {
            fixture: render(getattr(main_module, name), factory())
            for fixture, factory in FIXTURES.items()
        }
        for name in mapper_names()
    }


def test_every_mapper_has_a_snapshot_entry() -> None:
    frozen = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert sorted(frozen) == mapper_names()


@pytest.mark.parametrize("mapper_name", mapper_names())
def test_mapper_output_is_unchanged(mapper_name: str) -> None:
    frozen = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    mapper = getattr(main_module, mapper_name)

    for fixture_name, factory in FIXTURES.items():
        assert render(mapper, factory()) == frozen[mapper_name][fixture_name]
