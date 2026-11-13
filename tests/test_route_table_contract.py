"""Freeze the HTTP contract so a code move cannot silently change it.

Nine of ten refactor regressions are invisible to `mypy` and to the existing
parity test: `tests/test_openapi_contract.py` compares only paths and methods.
A handler rename changes the generated `operationId`, which breaks generated
clients, without failing any test today. This module closes that gap.

ADR-007 (amendment 2026-11-04) makes `docs/openapi.yaml` authoritative for
`operationId`, so the frozen snapshot is no longer an independent record of the
generated identifiers: `test_snapshot_matches_hand_written_operation_ids` also
asserts that the snapshot publishes exactly the identifiers the YAML declares.
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

    Only paths and methods are compared here, so a snapshot refreshed from the
    generator can never silently add or drop a documented operation. The
    `operationId` half of the contract is asserted separately by
    `test_snapshot_matches_hand_written_operation_ids`.
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


def test_snapshot_matches_hand_written_operation_ids() -> None:
    """The snapshot must publish exactly the identifiers the YAML declares.

    ADR-007 (amendment 2026-11-04) makes `docs/openapi.yaml` authoritative for
    `operationId`. The snapshot is produced from `app.openapi()`, so on its own
    it only proves the current generator output is frozen; without this check a
    handler rename followed by a snapshot refresh would silently bless a new,
    undocumented identifier. All divergences are aggregated so a fix is
    validated against every mismatch at once.
    """
    static = _static_document()
    documented = {
        (path, method.upper(), str(operation.get("operationId")))
        for path, item in static["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    }
    frozen = {
        (str(row["path"]), str(row["method"]), str(row["operation_id"])) for row in _snapshot()
    }

    documented_ids = {(path, method): operation_id for path, method, operation_id in documented}
    frozen_ids = {(path, method): operation_id for path, method, operation_id in frozen}

    missing = "<missing>"
    divergences = [
        f"{method} {path}: docs/openapi.yaml="
        f"{documented_ids.get((path, method), missing)!r} "
        f"tests/contracts/route_table.json="
        f"{frozen_ids.get((path, method), missing)!r}"
        for path, method in sorted(set(documented_ids) | set(frozen_ids))
        if documented_ids.get((path, method), missing) != frozen_ids.get((path, method), missing)
    ]

    assert not divergences, (
        f"{len(divergences)} of {len(set(documented_ids) | set(frozen_ids))} operations "
        "publish a different operationId in tests/contracts/route_table.json than in "
        "docs/openapi.yaml (ADR-007 makes the YAML authoritative; update the YAML "
        "before regenerating the snapshot):\n" + "\n".join(divergences)
    )
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


def _api_routes() -> list[APIRoute]:
    """Every ``APIRoute``, walking routers FastAPI keeps wrapped (0.162 ``_IncludedRouter``).

    Routers nest: app -> api_router -> module router. Walk recursively.
    """
    routes: list[APIRoute] = []

    def walk(router: object) -> None:
        for route in getattr(router, "routes", []):
            if isinstance(route, APIRoute):
                routes.append(route)
                continue
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(nested)

    walk(app)
    return routes


def _nested_route_paths() -> set[str]:
    """Collect paths from routers FastAPI keeps wrapped (0.162 `_IncludedRouter`)."""
    return {route.path_format for route in _api_routes()}


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


# --- T15: the credit ledger is read-only (issue #162) ------------------------
#
# Credits are an append-only ledger (CONTEXT.md, ADR-019). Writing a transaction
# or deleting one from the HTTP surface contradicts the ledger invariant and the
# final modeling, which has no `deleted_at` and no generic reference triple.
# Corrections are new transactions, so only the two reads stay published.

CREDIT_TRANSACTIONS_PATH = "/api/v1/workspace-credit-transactions"
CREDIT_TRANSACTION_PATH = "/api/v1/workspace-credit-transactions/{id}"
REMOVED_CREDIT_OPERATION_IDS = {
    "create_workspace_credit_transaction_api_v1_workspace_credit_transactions_post",
    "delete_workspace_credit_transaction_api_v1_workspace_credit_transactions__id__delete",
}
KEPT_CREDIT_OPERATION_IDS = {
    "list_workspace_credit_transactions_api_v1_workspace_credit_transactions_get",
    "get_workspace_credit_transaction_api_v1_workspace_credit_transactions__id__get",
}


def test_credit_ledger_exposes_no_write_operations() -> None:
    """Only GET list and GET by id survive on the credit ledger."""
    document = app.openapi()["paths"]

    assert set(document[CREDIT_TRANSACTIONS_PATH]) == {"get"}, (
        "POST must be removed from /api/v1/workspace-credit-transactions: a Credit "
        "Transaction is written by the capability that consumes Credits, never by a "
        f"client; got {sorted(document[CREDIT_TRANSACTIONS_PATH])}"
    )
    assert set(document[CREDIT_TRANSACTION_PATH]) == {"get"}, (
        "DELETE must be removed from /api/v1/workspace-credit-transactions/{id}: the "
        "ledger is append-only and has no soft delete, so corrections are new "
        f"transactions; got {sorted(document[CREDIT_TRANSACTION_PATH])}"
    )


def test_credit_ledger_operation_ids_are_the_two_reads() -> None:
    """Generated clients must lose the write identifiers, not keep orphan stubs."""
    published = {str(row["operation_id"]) for row in _route_table()}

    assert not (published & REMOVED_CREDIT_OPERATION_IDS), (
        "these operationIds belong to removed write operations: "
        f"{sorted(published & REMOVED_CREDIT_OPERATION_IDS)}"
    )
    assert KEPT_CREDIT_OPERATION_IDS <= published, (
        f"the read operations must stay published: {sorted(KEPT_CREDIT_OPERATION_IDS - published)}"
    )


# --- T20: subscription history is append-only (issue #163) -------------------
#
# ADR-019 makes `subscription_history` append-only: a plan or status change is a
# new event, never a rewrite. T20 ported that as a SQLite trigger, so the
# POST/PUT/DELETE handlers that still exist today cannot succeed — they reach the
# trigger and answer 500. The HTTP surface has to publish only the two reads,
# exactly like the credit ledger after T15. `EXPECTED_OPERATION_COUNT` in
# tests/test_openapi_operation_id_parity.py drops by the same three operations.

SUBSCRIPTION_HISTORY_PATH = "/api/v1/subscription-history"
SUBSCRIPTION_HISTORY_ITEM_PATH = "/api/v1/subscription-history/{id}"
REMOVED_SUBSCRIPTION_HISTORY_OPERATIONS = {
    ("POST", SUBSCRIPTION_HISTORY_PATH),
    ("PUT", SUBSCRIPTION_HISTORY_ITEM_PATH),
    ("DELETE", SUBSCRIPTION_HISTORY_ITEM_PATH),
}
KEPT_SUBSCRIPTION_HISTORY_OPERATIONS = {
    ("GET", SUBSCRIPTION_HISTORY_PATH),
    ("GET", SUBSCRIPTION_HISTORY_ITEM_PATH),
}
REMOVED_SUBSCRIPTION_HISTORY_OPERATION_IDS = {
    "create_subscription_history_api_v1_subscription_history_post",
    "update_subscription_history_api_v1_subscription_history__id__put",
    "delete_subscription_history_api_v1_subscription_history__id__delete",
}
KEPT_SUBSCRIPTION_HISTORY_OPERATION_IDS = {
    "list_subscription_history_api_v1_subscription_history_get",
    "get_subscription_history_api_v1_subscription_history__id__get",
}


def _served_operations() -> set[tuple[str, str]]:
    """`(method, path)` of every operation the application actually serves."""
    served: set[tuple[str, str]] = set()
    for route in _api_routes():
        for method in route.methods or ():
            served.add((method.upper(), route.path_format))
    return served


def test_subscription_history_exposes_no_write_operations() -> None:
    """Only GET list and GET by id survive on the append-only history."""
    document = app.openapi()["paths"]
    collection = document.get(SUBSCRIPTION_HISTORY_PATH, {})
    item = document.get(SUBSCRIPTION_HISTORY_ITEM_PATH, {})

    assert set(collection) == {"get"}, (
        "POST must be removed from /api/v1/subscription-history: subscription_history is "
        "append-only (ADR-019) and the T20 trigger refuses the INSERT the handler performs "
        f"after its read; got {sorted(collection)}"
    )
    assert set(item) == {"get"}, (
        "PUT and DELETE must be removed from /api/v1/subscription-history/{id}: a plan or "
        "status change is a new event, and the append-only trigger refuses both. Got "
        f"{sorted(item)}"
    )


def test_subscription_history_write_routes_are_not_served() -> None:
    """The schema and the served routes must agree; a hidden write route is still a write."""
    served = _served_operations()

    still_served = sorted(REMOVED_SUBSCRIPTION_HISTORY_OPERATIONS & served)
    assert not still_served, (
        "these write operations are still served by the application, so they answer 500 when "
        f"the append-only trigger fires: {still_served}"
    )
    missing = sorted(KEPT_SUBSCRIPTION_HISTORY_OPERATIONS - served)
    assert not missing, f"the read operations must stay served: {missing}"


def test_subscription_history_write_operations_are_absent_from_the_frozen_snapshot() -> None:
    """`tests/contracts/route_table.json` must lose the same three operations."""
    frozen = {(str(row["method"]), str(row["path"])) for row in _snapshot()}

    still_frozen = sorted(REMOVED_SUBSCRIPTION_HISTORY_OPERATIONS & frozen)
    assert not still_frozen, (
        "the frozen route table still publishes write operations on the append-only "
        f"subscription history: {still_frozen}"
    )
    missing = sorted(KEPT_SUBSCRIPTION_HISTORY_OPERATIONS - frozen)
    assert not missing, f"the frozen route table dropped the read operations: {missing}"


def test_subscription_history_operation_ids_are_the_two_reads() -> None:
    """Generated clients must lose the write identifiers, not keep orphan stubs."""
    published = {str(row["operation_id"]) for row in _route_table()}

    assert not (published & REMOVED_SUBSCRIPTION_HISTORY_OPERATION_IDS), (
        "these operationIds belong to removed write operations: "
        f"{sorted(published & REMOVED_SUBSCRIPTION_HISTORY_OPERATION_IDS)}"
    )
    assert KEPT_SUBSCRIPTION_HISTORY_OPERATION_IDS <= published, (
        "the read operations must stay published: "
        f"{sorted(KEPT_SUBSCRIPTION_HISTORY_OPERATION_IDS - published)}"
    )


# --- T16: the provider cache tables are retired (issue #164) ------------------
#
# ADR-031 drops `provider_customers` and `provider_subscriptions`: the final
# modeling has no table for a provider-side customer/subscription cache, and
# `billing_accounts`/`subscriptions` already own the provider identifiers. A route
# whose table is gone cannot answer, so the ten CRUD operations over the two
# collections leave the contract with the schema. `EXPECTED_OPERATION_COUNT` in
# tests/test_openapi_operation_id_parity.py drops by the same ten operations.

PROVIDER_CUSTOMER_PATH = "/api/v1/provider-customers"
PROVIDER_CUSTOMER_ITEM_PATH = "/api/v1/provider-customers/{id}"
PROVIDER_SUBSCRIPTION_PATH = "/api/v1/provider-subscriptions"
PROVIDER_SUBSCRIPTION_ITEM_PATH = "/api/v1/provider-subscriptions/{id}"
RETIRED_PROVIDER_PATHS = {
    PROVIDER_CUSTOMER_PATH,
    PROVIDER_CUSTOMER_ITEM_PATH,
    PROVIDER_SUBSCRIPTION_PATH,
    PROVIDER_SUBSCRIPTION_ITEM_PATH,
}
REMOVED_PROVIDER_OPERATIONS = {
    ("GET", PROVIDER_CUSTOMER_PATH),
    ("POST", PROVIDER_CUSTOMER_PATH),
    ("GET", PROVIDER_CUSTOMER_ITEM_PATH),
    ("PUT", PROVIDER_CUSTOMER_ITEM_PATH),
    ("DELETE", PROVIDER_CUSTOMER_ITEM_PATH),
    ("GET", PROVIDER_SUBSCRIPTION_PATH),
    ("POST", PROVIDER_SUBSCRIPTION_PATH),
    ("GET", PROVIDER_SUBSCRIPTION_ITEM_PATH),
    ("PUT", PROVIDER_SUBSCRIPTION_ITEM_PATH),
    ("DELETE", PROVIDER_SUBSCRIPTION_ITEM_PATH),
}
REMOVED_PROVIDER_OPERATION_IDS = {
    "list_provider_customers_api_v1_provider_customers_get",
    "create_provider_customer_api_v1_provider_customers_post",
    "get_provider_customer_api_v1_provider_customers__id__get",
    "update_provider_customer_api_v1_provider_customers__id__put",
    "delete_provider_customer_api_v1_provider_customers__id__delete",
    "list_provider_subscriptions_api_v1_provider_subscriptions_get",
    "create_provider_subscription_api_v1_provider_subscriptions_post",
    "get_provider_subscription_api_v1_provider_subscriptions__id__get",
    "update_provider_subscription_api_v1_provider_subscriptions__id__put",
    "delete_provider_subscription_api_v1_provider_subscriptions__id__delete",
}
# The rest of the provider surface is unrelated to the retirement and must keep
# every operation it publishes today.
KEPT_PROVIDER_OPERATIONS = {
    ("GET", "/api/v1/provider-webhook-events"),
    ("POST", "/api/v1/provider-webhook-events"),
    ("GET", "/api/v1/provider-webhook-events/{id}"),
    ("PUT", "/api/v1/provider-webhook-events/{id}"),
    ("DELETE", "/api/v1/provider-webhook-events/{id}"),
    ("GET", "/api/v1/provider-idempotency-keys"),
    ("POST", "/api/v1/provider-idempotency-keys"),
    ("GET", "/api/v1/provider-idempotency-keys/{id}"),
    ("PUT", "/api/v1/provider-idempotency-keys/{id}"),
    ("DELETE", "/api/v1/provider-idempotency-keys/{id}"),
    ("GET", "/api/v1/provider-disputes"),
    ("POST", "/api/v1/provider-disputes"),
    ("GET", "/api/v1/provider-disputes/{id}"),
    ("PUT", "/api/v1/provider-disputes/{id}"),
    ("DELETE", "/api/v1/provider-disputes/{id}"),
}


def test_provider_customer_and_subscription_paths_are_gone_from_the_contract() -> None:
    """The retired collections must not survive in either document."""
    generated = set(app.openapi()["paths"])
    documented = set(_static_document()["paths"])

    assert not (RETIRED_PROVIDER_PATHS & generated), (
        "app.openapi() still publishes the retired provider cache collections: "
        f"{sorted(RETIRED_PROVIDER_PATHS & generated)}"
    )
    assert not (RETIRED_PROVIDER_PATHS & documented), (
        "docs/openapi.yaml still documents the retired provider cache collections: "
        f"{sorted(RETIRED_PROVIDER_PATHS & documented)}"
    )


def test_provider_customer_and_subscription_routes_are_not_served() -> None:
    """A route left in the router would answer even with the path undocumented."""
    served = _served_operations()

    still_served = sorted(REMOVED_PROVIDER_OPERATIONS & served)
    assert not still_served, (
        "these operations are still served by the application although ADR-031 retired "
        f"their tables: {still_served}"
    )


def test_provider_customer_and_subscription_operations_left_the_frozen_snapshot() -> None:
    """`tests/contracts/route_table.json` must lose exactly the ten operations."""
    frozen = {(str(row["method"]), str(row["path"])) for row in _snapshot()}

    still_frozen = sorted(REMOVED_PROVIDER_OPERATIONS & frozen)
    assert not still_frozen, (
        f"the frozen route table still publishes the retired collections: {still_frozen}"
    )
    assert KEPT_PROVIDER_OPERATIONS <= frozen, (
        "the retirement must not touch the rest of the provider surface; missing from the "
        f"snapshot: {sorted(KEPT_PROVIDER_OPERATIONS - frozen)}"
    )


def test_provider_customer_and_subscription_operation_ids_are_not_published() -> None:
    """Generated clients must lose the identifiers, not keep orphan stubs."""
    published = {str(row["operation_id"]) for row in _route_table()}

    assert not (published & REMOVED_PROVIDER_OPERATION_IDS), (
        f"these operationIds belong to retired operations: "
        f"{sorted(published & REMOVED_PROVIDER_OPERATION_IDS)}"
    )


def test_retirement_removes_no_unrelated_provider_operation() -> None:
    """The delta is exactly the two collections, not a broader provider cleanup."""
    removed = REMOVED_PROVIDER_OPERATIONS
    assert len(removed) == 10, (
        f"the two retired collections carry 5 CRUD operations each; got {sorted(removed)}"
    )
    assert {path for _, path in removed} == RETIRED_PROVIDER_PATHS
    assert not (removed & KEPT_PROVIDER_OPERATIONS), sorted(removed & KEPT_PROVIDER_OPERATIONS)
