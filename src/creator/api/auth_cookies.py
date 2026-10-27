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
    secure = bool(settings.auth_cookie_secure)
    same_site = settings.auth_cookie_same_site
    response.set_cookie(
        settings.auth_cookie_access_name,
        session.access_token,
        max_age=session.expires_in,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path=settings.auth_cookie_access_path,
    )
    refresh_max_age = session.refresh_expires_in
    response.set_cookie(
        settings.auth_cookie_refresh_name,
        session.refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        secure=secure,
        samesite="strict" if same_site != "none" else "none",
        path=settings.auth_cookie_refresh_path,
    )
    response.set_cookie(
        settings.auth_cookie_csrf_name,
        csrf_token,
        max_age=settings.auth_csrf_ttl_seconds,
        httponly=False,
        secure=secure,
        samesite=same_site,
        path=settings.auth_cookie_csrf_path,
    )


def clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    for name, path in (
        (settings.auth_cookie_access_name, settings.auth_cookie_access_path),
        (settings.auth_cookie_refresh_name, settings.auth_cookie_refresh_path),
        (settings.auth_cookie_csrf_name, settings.auth_cookie_csrf_path),
    ):
        response.delete_cookie(name, path=path)
