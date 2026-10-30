"""The deny branches of the shared authorization helpers must stay exercised.

`creator/api/errors.py` reports 82% coverage because exactly the two
`raise HTTPException(status_code=403)` statements are never executed: every
existing HTTP test either asserts 401 (no principal at all) or uses an
`admin_app()` fixture that never reaches the guard. Since the modular
extraction, the callers live in `modules/*/router.py`, which
`[tool.coverage.run].omit` excludes, so a regression in an authorization guard
is invisible to coverage *and* to `tests/test_api.py`.

Routes are listed explicitly, with the guard they exercise, so a rename or a
removed guard fails here instead of silently degrading the suite.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_api import authorized_app

# Both guards must keep a structured code: a string detail is mapped to the
# generic `HTTP_ERROR` by the exception handler and the reason is lost.
ADMIN_ONLY_OPERATIONS = [
    ("/api/v1/users", "ADMIN_REQUIRED"),
    ("/api/v1/users/{id}", "ADMIN_REQUIRED"),
    ("/api/v1/coupons", "BILLING_ADMIN_REQUIRED"),
    ("/api/v1/plans", "BILLING_ADMIN_REQUIRED"),
]


def _concrete(path: str) -> str:
    return path.replace("{id}", str(uuid4()))


@pytest.mark.anyio
async def test_non_admin_principal_is_denied_on_admin_only_operations() -> None:
    failures: list[str] = []
    # `authorized_app` authenticates as a principal whose global_role is
    # "membro", so every admin guard must reject it.
    async with AsyncClient(
        transport=ASGITransport(app=authorized_app()), base_url="http://test"
    ) as client:
        for template, expected_code in ADMIN_ONLY_OPERATIONS:
            path = _concrete(template)
            response = await client.get(path)
            if response.status_code != 403:
                failures.append(f"GET {template} answered {response.status_code}, expected 403")
                continue
            body = response.json()
            if body.get("success") is not False:
                failures.append(f"GET {template} did not return a failure envelope")
            if not (body.get("error") or {}).get("message"):
                failures.append(f"GET {template} returned an error without a message")
            if not (body.get("meta") or {}).get("request_id"):
                failures.append(f"GET {template} returned an error without meta.request_id")
            if body["error"].get("code") != expected_code:
                failures.append(
                    f"GET {template} answered 403 with code {body['error'].get('code')!r}, "
                    f"expected {expected_code!r}"
                )

    assert not failures, "authorization denials regressed:\n" + "\n".join(failures)
