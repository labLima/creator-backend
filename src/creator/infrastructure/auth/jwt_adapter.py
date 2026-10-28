"""Creator-owned JWT adapter over the project's PyJWT 2.x dependency."""

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
