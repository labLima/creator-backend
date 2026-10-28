from __future__ import annotations

from uuid import UUID

from fastapi import Response

from creator.application.auth_ports import AuthTokenServices
from creator.config import Settings
from creator.domain.auth import IssuedSession


def csrf_for_session(
    session: IssuedSession, *, settings: Settings, token_services: AuthTokenServices
) -> str:
    session_id = UUID(session.principal.session_id or "")
    return token_services.csrf.issue(session_id=session_id, settings=settings)


def set_auth_cookies(
    response: Response,
    session: IssuedSession,
    *,
    csrf_token: str,
    settings: Settings,
) -> None:
    if not settings.auth_cookie_sessions_enabled:
        return
    policy = settings.auth_cookie_policy
    response.set_cookie(
        policy.access_name,
        session.access_token,
        max_age=policy.access_max_age(min(session.expires_in, session.refresh_expires_in)),
        httponly=policy.access_http_only,
        secure=policy.secure,
        samesite=policy.access_same_site,
        path=policy.access_path,
    )
    response.set_cookie(
        policy.refresh_name,
        session.refresh_token,
        max_age=policy.refresh_max_age(session.refresh_expires_in),
        httponly=policy.refresh_http_only,
        secure=policy.secure,
        samesite=policy.refresh_same_site,
        path=policy.refresh_path,
    )
    set_csrf_cookie(response, csrf_token, settings=settings)


def set_csrf_cookie(response: Response, token: str, *, settings: Settings) -> None:
    policy = settings.auth_cookie_policy
    response.set_cookie(
        policy.csrf_name,
        token,
        max_age=policy.csrf_max_age(),
        httponly=policy.csrf_http_only,
        secure=policy.secure,
        samesite=policy.access_same_site,
        path=policy.csrf_path,
    )


def clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    policy = settings.auth_cookie_policy
    for name, path in (
        (policy.access_name, policy.access_path),
        (policy.refresh_name, policy.refresh_path),
        (policy.csrf_name, policy.csrf_path),
    ):
        response.delete_cookie(name, path=path)
