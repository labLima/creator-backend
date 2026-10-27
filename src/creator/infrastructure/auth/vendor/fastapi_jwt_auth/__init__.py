"""Small Creator-owned compatibility surface for the patched JWT provider.

The upstream fastapi-jwt-auth 0.5.0 source is not imported by application code.
This module keeps the provider API behind infrastructure while using the
project's PyJWT 2.x dependency and its string-returning encode contract.
"""

from __future__ import annotations

from typing import Any, cast

import jwt as _jwt

ExpiredSignatureError = _jwt.ExpiredSignatureError
InvalidTokenError = _jwt.InvalidTokenError


def encode(payload: dict[str, object], secret: str, *, algorithm: str) -> str:
    return _jwt.encode(payload, secret, algorithm=algorithm)


def decode(
    token: str,
    secret: str,
    *,
    algorithms: list[str],
    audience: str,
    issuer: str,
    options: dict[str, object],
) -> dict[str, object]:
    return _jwt.decode(
        token,
        secret,
        algorithms=algorithms,
        audience=audience,
        issuer=issuer,
        options=cast(Any, options),
    )
