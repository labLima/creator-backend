"""Every protected operation must reject anonymous callers over real HTTP.

`tests/test_app_structure.py::test_business_routes_require_authenticated_principal`
only proves that a handler *declares* `current_user`, and it silently skips any
router that uses a relative decorator path (for example
`APIRouter(prefix="/api/v1/auth")`). `tests/test_api.py` asserts a 401 for two
of the 221 protected operations. Neither test executes the dependency graph of
the other 219.

After the modular extraction those 219 handlers live in `modules/*/router.py`,
which `[tool.coverage.run].omit` excludes, so a lost authentication dependency
is invisible to coverage as well. This module closes that gap the cheapest way
that gives real confidence: one unauthenticated request per operation through
the ASGI stack.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from creator.main import app
from tests.test_api import authenticated_app

CONTRACTS = Path(__file__).resolve().parent / "contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# Public by design.
# - login / signup / refresh bootstrap a session, so they cannot require one.
# - logout is idempotent on purpose: `logout_session` depends on
#   `get_optional_current_user` and answers 200 so a client can always clear
#   its own cookies.
PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}


def _protected_operations() -> list[tuple[str, str]]:
    operations = [
        (method.upper(), path)
        for path, path_item in app.openapi()["paths"].items()
        if path.startswith("/api/v1/") and path not in PUBLIC_PATHS
        for method in path_item
        if method in HTTP_METHODS
    ]
    # Guards against a refactor that silently detaches the module routers: an
    # empty or shrunken list would make the loop below pass vacuously. The
    # expectation comes from the frozen HTTP contract, not from the app, so
    # the two can only agree if every documented operation is really mounted.
    frozen = json.loads((CONTRACTS / "route_table.json").read_text(encoding="utf-8"))
    expected = {
        (str(row["method"]), str(row["path"]))
        for row in frozen
        if str(row["path"]).startswith("/api/v1/") and str(row["path"]) not in PUBLIC_PATHS
    }
    assert set(operations) == expected, (
        "operations mounted on the app differ from the frozen route table: "
        f"missing={sorted(expected - set(operations))} "
        f"unexpected={sorted(set(operations) - expected)}"
    )
    return operations


def _concrete_path(template: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid4()), template)


@pytest.mark.anyio
async def test_every_protected_operation_rejects_anonymous_requests() -> None:
    failures: list[str] = []
    async with AsyncClient(
        transport=ASGITransport(app=authenticated_app()), base_url="http://test"
    ) as client:
        for method, path in _protected_operations():
            response = await client.request(method, _concrete_path(path), json={})
            if response.status_code != 401:
                failures.append(f"{method} {path} answered {response.status_code}")
                continue
            body = response.json()
            code = (body.get("error") or {}).get("code")
            if code != "AUTHENTICATION_INVALID":
                failures.append(f"{method} {path} answered 401 with error code {code!r}")
            if not (body.get("meta") or {}).get("request_id"):
                failures.append(f"{method} {path} answered 401 without meta.request_id")

    assert not failures, "unauthenticated requests were not rejected:\n" + "\n".join(failures)
