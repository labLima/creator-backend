"""Freeze the HTTP contract so a code move cannot silently change it.

Nine of ten refactor regressions are invisible to `mypy` and to the existing
parity test: `tests/test_openapi_contract.py` compares only paths and methods.
A handler rename changes the generated `operationId`, which breaks generated
clients, without failing any test today. This module closes that gap.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.routing import APIRoute

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _route_table() -> list[dict[str, object]]:
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
    rows.sort(key=lambda row: (str(row["path"]), str(row["method"])))
    return rows


def _snapshot() -> list[dict[str, object]]:
    return json.loads((CONTRACTS / "route_table.json").read_text(encoding="utf-8"))


def _static_document() -> dict[str, object]:
    return yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))


def test_route_table_matches_frozen_snapshot() -> None:
    assert _route_table() == _snapshot()


def test_snapshot_matches_hand_written_paths_and_methods() -> None:
    """The snapshot must not drift from the hand-written contract.

    Only paths and methods are compared: `docs/openapi.yaml` predates the
    generated `operationId` scheme and 106 of its identifiers differ today.
    Making the snapshot agree with the generator must never be a way to
    silently redefine the documented surface.
    """
    static = _static_document()
    documented = {
        (path, method.upper())
        for path, item in static["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }
    frozen = {(str(row["path"]), str(row["method"])) for row in _snapshot()}

    assert frozen == documented


def test_operation_ids_are_unique() -> None:
    operation_ids = [str(row["operation_id"]) for row in _route_table()]

    assert len(operation_ids) == len(set(operation_ids))


def test_every_operation_has_a_tag() -> None:
    for row in _route_table():
        assert row["tags"], f"{row['method']} {row['path']} is untagged"


def test_documented_paths_are_served() -> None:
    """Every documented path resolves to a real route, not just a schema entry."""
    documented_paths = set(_static_document()["paths"])
    route_paths = {route.path_format for route in app.routes if isinstance(route, APIRoute)}

    assert documented_paths <= route_paths | _nested_route_paths()


def _nested_route_paths() -> set[str]:
    """Collect paths from routers that FastAPI keeps wrapped (0.162 `_IncludedRouter`)."""
    paths: set[str] = set()
    for route in app.routes:
        original = getattr(route, "original_router", None)
        if original is None:
            continue
        paths |= {child.path_format for child in original.routes if isinstance(child, APIRoute)}
    return paths


@pytest.mark.parametrize(
    ("specific", "generic"),
    [
        ("/api/v1/images/generate", "/api/v1/images/{id}"),
        ("/api/v1/generations/image-workflows", "/api/v1/generations/{id}"),
        ("/api/v1/generations/image-workflows/{id}", "/api/v1/generations/{id}"),
    ],
)
def test_specific_paths_are_declared_before_catch_all_paths(specific: str, generic: str) -> None:
    """Route matching is order dependent; moving routes must preserve precedence.

    Two paths at the same depth compete: `/images/generate` shadows
    `/images/{id}` if declared later. An exact parent path (`/contents`) does
    not compete with its child (`/contents/{id}`) and is therefore not listed.
    """
    document = app.openapi()
    if specific not in document["paths"] or generic not in document["paths"]:
        pytest.skip(f"{specific} or {generic} not part of the current contract")

    documented_order = list(document["paths"])
    assert documented_order.index(specific) < documented_order.index(generic)
