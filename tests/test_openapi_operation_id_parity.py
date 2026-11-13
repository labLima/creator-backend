"""Guard the `operationId` surface of the hand-written OpenAPI contract.

ADR-007 (amendment 2026-11-04) makes `docs/openapi.yaml` authoritative for
`operationId` and for per-operation error responses. A duplicate identifier
silently overrides another operation in generated clients, and an operation
without an identifier cannot be generated at all.

The static checks read the YAML as data only. `operationId` parity against the
running application is compared through the published `app.openapi()` document,
which is the seam that distinguishes the identifier a generated client would
receive from the one the YAML declares. On the installed FastAPI (0.162),
`APIRoute.operation_id` stays `None` until a route declares an id explicitly:
FastAPI only derives the identifier while building the schema, so the attribute
is a reliable signal that a route declared its contract instead of inheriting a
generated id.

The error-response checks below read the same two public seams. `403`, `404` and
`409` are compared per operation; `401`, `429` and `500` are document-wide
conventions. Response component names are normalized to the last segment of
their `$ref` so `#/components/responses/Forbidden` and `Forbidden` compare equal.

The broader path/method/security parity lives in `tests/test_openapi_contract.py`
and the frozen route table in `tests/test_route_table_contract.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi.routing import APIRoute

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = PROJECT_ROOT / "docs" / "openapi.yaml"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
# 225 `/api/v1` operations plus the three System operations (/health,
# /health/live, /metrics). The original 227 figure in issue 0051 predates Activity
# Events; the two credit-ledger write operations were removed in T15 (issue #162)
# because a Credit Transaction belongs to an append-only ledger, and the three
# subscription-history writes were removed in T20 (issue #163) because
# `subscription_history` is append-only too: 231 - 3 = 228.
EXPECTED_OPERATION_COUNT = 228

NOTIFICATION_PREFERENCE_PATH = "/api/v1/notification-preferences/{id}"
RESOURCE_ID_REF = {"$ref": "#/components/parameters/ResourceId"}
# The normalized form of `ResourceId`: `(name, in, required, type, format)`.
# `_normalized_parameters` resolves the YAML `$ref` and FastAPI's inline
# parameter to this tuple, so both documents are compared on equal footing.
RESOURCE_ID_SHAPE = ("id", "path", True, "string", "uuid")
LOGIN_REJECTED_COMPONENT = "LoginRejected"
LOGIN_REJECTED_CODE = "LOGIN_REJECTED"

# ADR-007 (amendment 2026-11-04): these statuses are compared per operation.
PER_OPERATION_ERROR_STATUSES = ("403", "404", "409")
# ADR-007 (amendment 2026-11-04): these are required on every `/api/v1` operation.
GLOBAL_ERROR_STATUSES = ("401", "429", "500")
CANONICAL_VALIDATION_RESPONSE = "ValidationFailed"
# Signup documents a domain-specific 422 (`WeakPassword`) that still resolves to
# the canonical `ErrorResponse` envelope; it is not FastAPI's default shape.
CANONICAL_VALIDATION_RESPONSES = frozenset({"ValidationFailed", "WeakPassword"})
CANONICAL_ERROR_SCHEMA = "ErrorResponse"
# Response components referenced by `docs/openapi.yaml` that `app.openapi()` must
# publish for generated clients to resolve the same error surface.
REQUIRED_ERROR_RESPONSE_COMPONENTS = frozenset(
    {
        "Forbidden",
        "NotFound",
        "Conflict",
        "ValidationFailed",
        "WorkspaceNotFound",
        "WorkspaceAccessDenied",
        "EmailAlreadyRegistered",
        "RefreshInProgress",
        "Unauthorized",
        "RateLimitExceeded",
        "InternalServerError",
    }
)


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


def _api_v1_operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index the operations covered by the global `/api/v1` error conventions."""
    return {
        (path, method): operation
        for (path, method), operation in _operations_by_slug(document).items()
        if path.startswith("/api/v1/")
    }


def _component_name(response: Any) -> str:
    """Normalize a response to the component name its `$ref` points at.

    `#/components/responses/Forbidden` becomes `Forbidden`. Responses without a
    `$ref` are reported as `<inline>`, which never matches a named component.
    """
    if not isinstance(response, dict):
        return repr(response)
    ref = response.get("$ref")
    if not isinstance(ref, str):
        return "<inline>"
    return ref.rsplit("/", 1)[-1]


def _normalized_error_codes(response: Any) -> tuple[str, ...]:
    """Return the response's `x-error-codes` sorted, or `()` when it declares none.

    Sorting normalizes declaration order so the comparison is about the set of
    codes a generated client would branch on, not the YAML key order.
    """
    if not isinstance(response, dict):
        return ()
    codes = response.get("x-error-codes")
    if not isinstance(codes, list):
        return ()
    return tuple(sorted(str(code) for code in codes))


def _response_shape(response: Any) -> str:
    """Normalize a response to the shape a generated client would resolve.

    A `$ref` to `#/components/responses/ValidationFailed` becomes
    `ValidationFailed`. An inline JSON response whose schema is a `$ref` becomes
    `inline:HTTPValidationError`, so FastAPI's default envelope stays
    distinguishable from the canonical named component. Anything else is
    `<inline>`.
    """
    component = _component_name(response)
    if component != "<inline>":
        return component
    schema_name = _inline_schema_name(response)
    if schema_name is None:
        return "<inline>"
    return f"inline:{schema_name}"


def _error_responses_by_status(
    operation: dict[str, Any], statuses: tuple[str, ...]
) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Map each documented status to its component name and normalized error codes."""
    responses = operation.get("responses", {})
    documented = (status for status in statuses if status in responses)
    return {
        status: (_component_name(responses[status]), _normalized_error_codes(responses[status]))
        for status in documented
    }


def _normalized_parameters(
    operation: dict[str, Any], document: dict[str, Any]
) -> tuple[tuple[str, str, bool, str, str], ...]:
    """Normalize an operation's parameters, resolving `$ref` against `document`.

    FastAPI publishes a shared parameter inline and adds a `title`, while the
    hand-written document references the same parameter as a component.
    Comparing `(name, in, required, type, format)` makes both spellings equal
    without weakening the check: a different name, location, required flag or
    schema still diverges.
    """
    components = document.get("components", {}).get("parameters", {})
    normalized: list[tuple[str, str, bool, str, str]] = []
    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        resolved = parameter
        ref = parameter.get("$ref")
        if isinstance(ref, str):
            resolved = components.get(ref.rsplit("/", 1)[-1], {})
        schema = resolved.get("schema", {})
        normalized.append(
            (
                str(resolved.get("name")),
                str(resolved.get("in")),
                bool(resolved.get("required")),
                str(schema.get("type")),
                str(schema.get("format")),
            )
        )
    return tuple(sorted(normalized))


def _inline_schema_name(response: Any) -> str | None:
    """Return the schema component for an inline JSON response, if any."""
    if not isinstance(response, dict):
        return None
    schema = response.get("content", {}).get("application/json", {}).get("schema")
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return None
    return ref.rsplit("/", 1)[-1]


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


def _declared_api_routes() -> list[APIRoute]:
    """Collect every `APIRoute`, walking routers FastAPI keeps wrapped.

    Routers nest: app -> api_router -> module router. FastAPI 0.162 wraps an
    included router instead of flattening it, so a flat scan of `app.routes`
    would miss most routes and let this guard pass vacuously.
    """
    routes: list[APIRoute] = []

    def walk(router: Any) -> None:
        for route in getattr(router, "routes", []):
            if isinstance(route, APIRoute):
                routes.append(route)
                continue
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(nested)

    walk(app)
    return routes


def test_every_api_route_declares_explicit_operation_id() -> None:
    """Every route must declare its `operationId` instead of deriving one.

    On the installed FastAPI (0.162) a route without an explicit id keeps
    `APIRoute.operation_id is None`; the identifier is only synthesized while
    the schema is built. That makes the attribute the seam between an explicit
    contract declaration and a handler-derived id: a renamed handler on an
    undeclared route would change the published `operationId` without touching
    this attribute. The route count is frozen so the walk cannot pass
    vacuously on an empty or truncated traversal.
    """
    routes = _declared_api_routes()
    undeclared = sorted(
        f"{','.join(sorted(route.methods or ()))} {route.path_format}"
        for route in routes
        if route.operation_id is None
    )

    assert len(routes) == EXPECTED_OPERATION_COUNT, (
        f"walked {len(routes)} APIRoutes, expected the frozen "
        f"{EXPECTED_OPERATION_COUNT}; the route walk missed nested routers or the "
        "surface moved"
    )
    assert not undeclared, (
        f"{len(undeclared)} routes do not declare an explicit operationId and would "
        "publish a handler-derived id (ADR-007 requires an explicit, camelCase id "
        f"matching docs/openapi.yaml): {undeclared}"
    )


def test_operation_id_parity_compares_every_documented_operation() -> None:
    """Guard the parity test against passing vacuously on an empty intersection.

    The parity test intersects both documents. If a path or method disappeared
    from `app.openapi()`, the intersection would shrink and the assertion would
    keep passing while silently covering less. The compared set must therefore
    equal the complete YAML surface, which is frozen at
    `EXPECTED_OPERATION_COUNT` (225 `/api/v1` operations plus three System ones).
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
    """The GET was copied from the Assets collection and must describe a preference.

    The same surface is asserted on `app.openapi()`, because a generated client
    reads the application document, not the YAML; checking only the YAML would
    let the served contract drift while this test stayed green. Parameters are
    normalized so the YAML `$ref` and FastAPI's inline `id` parameter compare
    equal.
    """
    static = _static_contract()
    generated = app.openapi()
    operation = static["paths"][NOTIFICATION_PREFERENCE_PATH]["get"]
    generated_operation = generated["paths"][NOTIFICATION_PREFERENCE_PATH]["get"]
    responses = operation["responses"]
    generated_responses = generated_operation["responses"]

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

    assert generated_operation["operationId"] == "getNotificationPreference", (
        "app.openapi() publishes a different id for the notification preference GET: "
        f"{generated_operation['operationId']!r}"
    )
    assert generated_operation.get("tags") == ["Notifications"], (
        f"app.openapi() tags the notification preference GET {generated_operation.get('tags')!r}"
    )
    assert RESOURCE_ID_SHAPE in _normalized_parameters(operation, static), (
        "the notification preference GET must take the ResourceId path parameter: "
        f"{_normalized_parameters(operation, static)!r}"
    )
    assert RESOURCE_ID_SHAPE in _normalized_parameters(generated_operation, generated), (
        "app.openapi() does not publish the ResourceId path parameter for the "
        f"notification preference GET: {_normalized_parameters(generated_operation, generated)!r}"
    )
    assert "404" in generated_responses, (
        "app.openapi() does not publish the documented 404 for the notification "
        f"preference GET: {sorted(generated_responses)}"
    )

    success_description = responses["200"]["description"].lower()
    assert "preference" in success_description, (
        f"the 200 description does not describe a notification preference: {success_description!r}"
    )
    assert "asset" not in success_description, (
        f"the 200 description was copied from the Assets collection: {success_description!r}"
    )


def test_auth_login_401_is_login_rejected() -> None:
    """`POST /api/v1/auth/login` must advertise the specific login rejection.

    A generic `Unauthorized` hides the difference between a bad credential and
    an expired session, which is exactly the branch a generated client has to
    take. Both documents must publish the `LoginRejected` component and the
    `LOGIN_REJECTED` code the app injects for this operation.
    """
    slug = ("/api/v1/auth/login", "post")
    static_response = _operations_by_slug(_static_contract())[slug]["responses"]["401"]
    generated_response = _operations_by_slug(app.openapi())[slug]["responses"]["401"]

    assert _component_name(static_response) == LOGIN_REJECTED_COMPONENT, (
        "docs/openapi.yaml documents a different 401 component for auth login: "
        f"{_component_name(static_response)!r}"
    )
    assert _component_name(generated_response) == LOGIN_REJECTED_COMPONENT, (
        "app.openapi() documents a different 401 component for auth login: "
        f"{_component_name(generated_response)!r}"
    )
    assert list(_normalized_error_codes(static_response)) == [LOGIN_REJECTED_CODE], (
        "docs/openapi.yaml documents different 401 x-error-codes for auth login: "
        f"{list(_normalized_error_codes(static_response))!r}"
    )
    assert list(_normalized_error_codes(generated_response)) == [LOGIN_REJECTED_CODE], (
        "app.openapi() documents different 401 x-error-codes for auth login: "
        f"{list(_normalized_error_codes(generated_response))!r}"
    )


def test_error_responses_403_404_409_match_static_contract() -> None:
    """`403`, `404` and `409` must match per operation, including codes.

    ADR-007 (amendment 2026-11-04) compares these statuses per operation because
    they describe resource-specific failures (forbidden, missing, conflicting)
    that cannot be inferred globally. The comparison normalizes each response to
    the last segment of its `$ref`, so `Forbidden`, `NotFound`,
    `WorkspaceNotFound`, `Conflict`, `EmailAlreadyRegistered` and
    `RefreshInProgress` are distinguishable. It also compares `x-error-codes`
    sorted, because those codes are the branch points of a generated client and
    an undocumented code in either document is a real drift. All divergences are
    reported together so a fix is not validated one operation at a time.
    """
    static_operations = _operations_by_slug(_static_contract())
    generated_operations = _operations_by_slug(app.openapi())

    compared = sorted(set(static_operations) & set(generated_operations))
    divergences: list[str] = []
    for path, method in compared:
        static_problems = _error_responses_by_status(
            static_operations[(path, method)], PER_OPERATION_ERROR_STATUSES
        )
        generated_problems = _error_responses_by_status(
            generated_operations[(path, method)], PER_OPERATION_ERROR_STATUSES
        )
        if static_problems == generated_problems:
            continue
        differences = [
            f"{status} docs/openapi.yaml={static_problems.get(status)!r} "
            f"app.openapi()={generated_problems.get(status)!r}"
            for status in PER_OPERATION_ERROR_STATUSES
            if static_problems.get(status) != generated_problems.get(status)
        ]
        divergences.append(f"{method.upper()} {path}: " + "; ".join(differences))

    assert not divergences, (
        f"{len(divergences)} of {len(compared)} operations document a different "
        "403/404/409 surface in app.openapi() than in docs/openapi.yaml (ADR-007 "
        "compares these statuses per operation; each value is "
        "(component_name, x-error-codes) with the codes sorted):\n" + "\n".join(divergences)
    )


def test_global_error_conventions_are_documented() -> None:
    """Global error conventions are declared once instead of per operation.

    The app injects `401`, `429` and `500` into every `/api/v1` operation in its
    OpenAPI post-processor, so those statuses are conventions rather than route
    declarations. The YAML documents `401` per operation, `429` through
    `x-rate-limit.response` (`RateLimitExceeded`) and `500` through the
    `InternalServerError` component; repeating them on all 227 `/api/v1`
    operations would add hundreds of artificial blocks. Where the YAML declares
    a provider-specific `429`/`500` component (`AuthRateLimited`,
    `LlmProviderRateLimited`, `SignupFailed`, `AuthMisconfigured`, ...) instead
    of the global one, that divergence is a deliberate exception documented in
    issue 0051, not silent drift. `422` is out of scope here: it is a validation
    convention handled by `test_generated_422_matches_static_contract`, not a
    globally injected status.
    """
    static = _static_contract()
    generated = app.openapi()

    missing_from_app = [
        f"app.openapi() {method.upper()} {path} lacks {status}"
        for (path, method), operation in sorted(_api_v1_operations(generated).items())
        for status in GLOBAL_ERROR_STATUSES
        if status not in operation.get("responses", {})
    ]
    missing_from_yaml = [
        f"docs/openapi.yaml {method.upper()} {path} lacks 401"
        for (path, method), operation in sorted(_api_v1_operations(static).items())
        if "401" not in operation.get("responses", {})
    ]

    rate_limit_response = static.get("x-rate-limit", {}).get("response", {})
    assert rate_limit_response.get("$ref") == "#/components/responses/RateLimitExceeded", (
        "docs/openapi.yaml must document the global 429 convention through "
        "`x-rate-limit.response.$ref = '#/components/responses/RateLimitExceeded'`: "
        f"{rate_limit_response!r}"
    )

    static_responses = static.get("components", {}).get("responses", {})
    assert "InternalServerError" in static_responses, (
        "docs/openapi.yaml must document the global 500 convention through the "
        f"`InternalServerError` response component; available: {sorted(static_responses)}"
    )

    assert not missing_from_app, (
        f"{len(missing_from_app)} /api/v1 operation/status pairs in app.openapi() "
        "lack a globally required error response (401, 429 and 500 are attached to "
        "every generated /api/v1 operation):\n" + "\n".join(missing_from_app)
    )
    assert not missing_from_yaml, (
        f"{len(missing_from_yaml)} /api/v1 operations in docs/openapi.yaml lack the "
        "per-operation 401 response:\n" + "\n".join(missing_from_yaml)
    )


def test_yaml_422_responses_are_covered_by_generated_document() -> None:
    """A `422` documented in the YAML must also exist in `app.openapi()`.

    Presence is not compared in the other direction: FastAPI adds `422` to every
    operation with request validation, while the YAML documents it only where it
    is relevant. But the YAML must never promise a validation response the
    application does not publish.
    """
    static_operations = _operations_by_slug(_static_contract())
    generated_operations = _operations_by_slug(app.openapi())

    uncovered = sorted(
        f"{method.upper()} {path}"
        for (path, method), operation in static_operations.items()
        if "422" in operation.get("responses", {})
        and "422" not in generated_operations.get((path, method), {}).get("responses", {})
    )

    assert not uncovered, (
        "docs/openapi.yaml documents a 422 response that app.openapi() does not "
        f"publish: {uncovered}"
    )


def test_generated_422_matches_static_contract() -> None:
    """A documented `422` must resolve to the same shape and codes in both documents.

    ADR-007 (amendment 2026-11-04) keeps `ErrorResponse`/`ValidationFailed` as
    the canonical envelope, so an inline `HTTPValidationError` schema or a
    bespoke component in the YAML is a real divergence, not a formatting
    detail: a client generated from the YAML branches on a different type than
    one generated from `app.openapi()`. `x-error-codes` are compared too, since
    they are the branch points a generated client reads when the documented
    operation narrows the failure (signup `WeakPassword`, content and image
    workflow domain errors); operations without operation-level codes normalize
    to `()` on both sides. Only operations the YAML documents as `422` are
    compared, because FastAPI emits `422` for every operation with validation
    and presence is not part of this gate. All divergences are aggregated so a
    fix is validated against every mismatch at once.
    """
    static_operations = _operations_by_slug(_static_contract())
    generated_operations = _operations_by_slug(app.openapi())

    documented_422 = sorted(
        (path, method)
        for (path, method), operation in static_operations.items()
        if "422" in operation.get("responses", {})
    )

    divergences: list[str] = []
    for path, method in documented_422:
        static_response = static_operations[(path, method)]["responses"]["422"]
        generated_response = (
            generated_operations.get((path, method), {}).get("responses", {}).get("422")
        )
        static_shape = _response_shape(static_response)
        generated_shape = (
            "<missing>" if generated_response is None else _response_shape(generated_response)
        )
        static_codes = _normalized_error_codes(static_response)
        generated_codes = _normalized_error_codes(generated_response)
        if static_shape == generated_shape and static_codes == generated_codes:
            continue
        divergences.append(
            f"{method.upper()} {path}: shape docs/openapi.yaml={static_shape!r} "
            f"app.openapi()={generated_shape!r}; x-error-codes "
            f"docs/openapi.yaml={list(static_codes)!r} "
            f"app.openapi()={list(generated_codes)!r}"
        )

    assert not divergences, (
        f"{len(divergences)} of {len(documented_422)} operations document a different "
        "422 shape or x-error-codes in app.openapi() than in docs/openapi.yaml (names "
        "are the last segment of the `$ref`, or `inline:<Schema>` for an inline "
        "schema; codes are sorted):\n" + "\n".join(divergences)
    )


def test_generated_validation_errors_use_canonical_error_envelope() -> None:
    """Every generated `422` must use the canonical `ErrorResponse` envelope.

    ADR-007 (amendment 2026-11-04) keeps `ErrorResponse`/`ValidationFailed` as the
    canonical error shape. FastAPI's default `HTTPValidationError` is a different
    envelope and must not leak into the published contract.
    """
    non_canonical: list[str] = []
    for (path, method), operation in sorted(_operations_by_slug(app.openapi()).items()):
        response = operation.get("responses", {}).get("422")
        if response is None:
            continue
        component = _component_name(response)
        if component in CANONICAL_VALIDATION_RESPONSES:
            continue
        schema_name = _inline_schema_name(response)
        if component == "<inline>" and schema_name == CANONICAL_ERROR_SCHEMA:
            continue
        shape = component if component != "<inline>" else f"inline:{schema_name}"
        non_canonical.append(f"{method.upper()} {path}: 422 resolves to {shape!r}")

    assert not non_canonical, (
        f"{len(non_canonical)} generated 422 responses do not use the canonical "
        f"{CANONICAL_VALIDATION_RESPONSE!r}/{CANONICAL_ERROR_SCHEMA!r} envelope:\n"
        + "\n".join(non_canonical)
    )


def test_error_response_components_exist_in_generated_document() -> None:
    """`app.openapi()` must publish the response components `docs/openapi.yaml` references.

    A client generated from the app cannot resolve `#/components/responses/NotFound`
    or `#/components/responses/ValidationFailed` if the component is absent, even
    when the per-operation status codes line up.
    """
    generated = app.openapi()
    available = set(generated.get("components", {}).get("responses", {}))
    missing = sorted(REQUIRED_ERROR_RESPONSE_COMPONENTS - available)

    assert not missing, (
        f"app.openapi() is missing {len(missing)} error response components "
        f"referenced by docs/openapi.yaml: {missing}"
    )
