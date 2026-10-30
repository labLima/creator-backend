from __future__ import annotations

from uuid import UUID

from fastapi import Response

from creator.application.auth_ports import AuthTokenServices, CookieSpec, CookieTransport
from creator.application.auth_types import IssuedSession
from creator.config import Settings


class FastApiCookieTransport:
    """FastAPI adapter for the transport-neutral cookie port."""

    def __init__(self, response: Response) -> None:
        self._response = response

    def set(self, cookie: CookieSpec) -> None:
        self._response.set_cookie(
            cookie.name,
            cookie.value,
            max_age=cookie.max_age,
            httponly=cookie.http_only,
            secure=cookie.secure,
            samesite=cookie.same_site,
            path=cookie.path,
            domain=cookie.domain,
        )

    def delete(self, *, name: str, path: str) -> None:
        self._response.delete_cookie(name, path=path)


def csrf_for_session(
    session: IssuedSession, *, settings: Settings, token_services: AuthTokenServices
) -> str:
    session_id = UUID(session.principal.session_id or "")
    return token_services.csrf.issue(session_id=session_id, settings=settings)


def set_auth_cookies(
    transport: CookieTransport,
    session: IssuedSession,
    *,
    csrf_token: str,
    settings: Settings,
) -> None:
    policy = settings.auth_cookie_policy
    transport.set(
        CookieSpec(
            name=policy.access_name,
            value=session.access_token,
            max_age=policy.access_max_age(min(session.expires_in, session.refresh_expires_in)),
            http_only=policy.access_http_only,
            secure=policy.secure,
            same_site=policy.access_same_site,
            path=policy.access_path,
            domain=policy.domain,
        )
    )
    transport.set(
        CookieSpec(
            name=policy.refresh_name,
            value=session.refresh_token,
            max_age=policy.refresh_max_age(session.refresh_expires_in),
            http_only=policy.refresh_http_only,
            secure=policy.secure,
            same_site=policy.refresh_same_site,
            path=policy.refresh_path,
            domain=policy.domain,
        )
    )
    set_csrf_cookie(transport, csrf_token, settings=settings)


def set_csrf_cookie(transport: CookieTransport, token: str, *, settings: Settings) -> None:
    policy = settings.auth_cookie_policy
    transport.set(
        CookieSpec(
            name=policy.csrf_name,
            value=token,
            max_age=policy.csrf_max_age(),
            http_only=policy.csrf_http_only,
            secure=policy.secure,
            same_site=policy.access_same_site,
            path=policy.csrf_path,
            domain=policy.domain,
        )
    )


def clear_auth_cookies(transport: CookieTransport, *, settings: Settings) -> None:
    policy = settings.auth_cookie_policy
    for name, path in (
        (policy.access_name, policy.access_path),
        (policy.refresh_name, policy.refresh_path),
        (policy.csrf_name, policy.csrf_path),
    ):
        transport.delete(name=name, path=path)
