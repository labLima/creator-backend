"""Guard the `operationId` surface of the hand-written OpenAPI contract.

ADR-007 (amendment 2026-11-04) makes `docs/openapi.yaml` authoritative for
`operationId` and for per-operation error responses. A duplicate identifier
silently overrides another operation in generated clients, and an operation
without an identifier cannot be generated at all.

The static checks read the YAML as data only. `operationId` parity against the
running application is compared through the published `app.openapi()` document,
which is the only seam that distinguishes the identifier a generated client
would receive from the one the YAML declares; `APIRoute.operation_id` is filled
by FastAPI even when it is derived automatically, so it cannot tell an explicit
id from a generated one.

The broader path/method/security parity lives in `tests/test_openapi_contract.py`
and the frozen route table in `tests/test_route_table_contract.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = PROJECT_ROOT / "docs" / "openapi.yaml"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
# 224 `/api/v1` operations plus the three System operations (/health,
# /health/live, /metrics). The 227 figure in issue 0051 is document-wide.
EXPECTED_OPERATION_COUNT = 227

NOTIFICATION_PREFERENCE_PATH = "/api/v1/notification-preferences/{id}"
RESOURCE_ID_REF = {"$ref": "#/components/parameters/ResourceId"}


def _static_contract() -> dict[str, Any]:
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def _documented_operations() -> list[tuple[str, str, dict[str, Any]]]:
    """Return `(path, method, operation)` for every documented HTTP operation.

    The whole document is covered on purpose: `operationId` uniqueness is a
    document-level invariant, and the 227 operations cited by issue 0051 are
    224 `/api/v1` routes plus three System routes.
    """
    return [
        (path, method, operation)
        for path, item in _static_contract()["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]


def _operations_by_slug(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index `(path, method)` to its operation object for one OpenAPI document."""
    return {
        (path, method): operation
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    }


def test_generated_operation_id_matches_static_contract() -> None:
    """Every shared `(path, method)` must publish the YAML's `operationId` verbatim.

    ADR-007 (amendment 2026-11-04) makes `docs/openapi.yaml` authoritative: a
    client generated from the static contract and one generated from
    `app.openapi()` must expose the same method names. All divergences are
    reported together so a fix is not validated one operation at a time.
    """
    static_operations = _operations_by_slug(_static_contract())
    generated_operations = _operations_by_slug(app.openapi())

    compared = sorted(set(static_operations) & set(generated_operations))
    divergences = [
        (
            f"{method.upper()} {path}: "
            f"docs/openapi.yaml={static_operations[(path, method)].get('operationId')!r} "
            f"app.openapi()={generated_operations[(path, method)].get('operationId')!r}"
        )
        for path, method in compared
        if static_operations[(path, method)].get("operationId")
        != generated_operations[(path, method)].get("operationId")
    ]

    assert not divergences, (
        f"{len(divergences)} of {len(compared)} operations publish a different "
        "operationId in app.openapi() than in docs/openapi.yaml (ADR-007 makes the "
        "YAML authoritative):\n" + "\n".join(divergences)
    )


def test_operation_id_parity_compares_every_documented_operation() -> None:
    """Guard the parity test against passing vacuously on an empty intersection.

    The parity test intersects both documents. If a path or method disappeared
    from `app.openapi()`, the intersection would shrink and the assertion would
    keep passing while silently covering less. The compared set must therefore
    equal the complete YAML surface, which is frozen at
    `EXPECTED_OPERATION_COUNT` (224 `/api/v1` operations plus three System ones).
    """
    static_operations = _operations_by_slug(_static_contract())
    generated_operations = _operations_by_slug(app.openapi())

    unnoted = sorted(
        f"{method.upper()} {path}"
        for path, method in static_operations.keys() - generated_operations.keys()
    )
    assert not unnoted, (
        "docs/openapi.yaml documents operations that app.openapi() does not publish; "
        f"operationId parity cannot cover them: {unnoted}"
    )

    extra = sorted(
        f"{method.upper()} {path}"
        for path, method in generated_operations.keys() - static_operations.keys()
    )
    assert not extra, (
        "app.openapi() publishes operations absent from docs/openapi.yaml; they would "
        f"escape operationId parity: {extra}"
    )

    assert len(static_operations) == EXPECTED_OPERATION_COUNT, (
        f"the compared surface has {len(static_operations)} operations, "
        f"expected the frozen {EXPECTED_OPERATION_COUNT}; the contract moved"
    )


def test_static_contract_has_unique_operation_ids() -> None:
    operations = _documented_operations()
    assert len(operations) == EXPECTED_OPERATION_COUNT, (
        f"docs/openapi.yaml documents {len(operations)} operations, "
        f"expected {EXPECTED_OPERATION_COUNT}; the frozen surface moved"
    )

    locations: dict[object, list[str]] = {}
    for path, method, operation in operations:
        operation_id = operation.get("operationId")
        locations.setdefault(operation_id, []).append(f"{method.upper()} {path}")

    duplicates = {
        str(operation_id): sorted(places)
        for operation_id, places in sorted(locations.items(), key=lambda item: str(item[0]))
        if len(places) > 1
    }
    assert not duplicates, (
        "docs/openapi.yaml declares duplicate operationIds (generated clients would "
        f"collapse them): {duplicates}"
    )

    operation_ids = [operation.get("operationId") for _, _, operation in operations]
    assert len(operation_ids) == len(set(operation_ids)), (
        f"{len(operation_ids)} operations must publish {len(operation_ids)} distinct ids"
    )


def test_static_contract_declares_operation_id_for_every_operation() -> None:
    missing = [
        f"{method.upper()} {path}"
        for path, method, operation in _documented_operations()
        if not operation.get("operationId")
    ]

    assert not missing, (
        f"docs/openapi.yaml operations without an operationId cannot be code-generated: {missing}"
    )


def test_notification_preference_get_is_a_get_operation() -> None:
    """The GET was copied from the Assets collection and must describe a preference."""
    operation = _static_contract()["paths"][NOTIFICATION_PREFERENCE_PATH]["get"]
    responses = operation["responses"]

    assert operation["operationId"] == "getNotificationPreference", (
        "the notification preference GET still reuses another operation's id: "
        f"{operation['operationId']!r}"
    )
    assert operation.get("tags") == ["Notifications"], (
        f"the notification preference GET is tagged {operation.get('tags')!r}"
    )
    assert RESOURCE_ID_REF in operation.get("parameters", []), (
        "the notification preference GET must take the shared ResourceId path parameter: "
        f"{operation.get('parameters')!r}"
    )
    assert {"200", "401"} <= set(responses), (
        f"the notification preference GET is missing documented success/auth responses: "
        f"{sorted(responses)}"
    )
    assert "404" in responses, (
        "the notification preference GET can resolve nothing and must document 404: "
        f"{sorted(responses)}"
    )

    success_description = responses["200"]["description"].lower()
    assert "preference" in success_description, (
        f"the 200 description does not describe a notification preference: {success_description!r}"
    )
    assert "asset" not in success_description, (
        f"the 200 description was copied from the Assets collection: {success_description!r}"
    )
