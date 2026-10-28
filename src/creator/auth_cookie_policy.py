from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from creator.config import Settings

CookieSameSite = Literal["strict", "lax", "none"]


@dataclass(frozen=True, slots=True)
class AuthCookiePolicy:
    """Resolved cookie transport policy, independent of FastAPI."""

    access_name: str
    refresh_name: str
    csrf_name: str
    access_path: str
    refresh_path: str
    csrf_path: str
    access_same_site: CookieSameSite
    refresh_same_site: CookieSameSite
    secure: bool
    access_http_only: bool
    refresh_http_only: bool
    csrf_http_only: bool
    csrf_header_name: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    csrf_ttl_seconds: int
    session_absolute_ttl_seconds: int
    domain: None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> AuthCookiePolicy:
        same_site = settings.auth_cookie_same_site
        refresh_same_site: CookieSameSite = "none" if same_site == "none" else "strict"
        return cls(
            access_name=settings.auth_cookie_access_name,
            refresh_name=settings.auth_cookie_refresh_name,
            csrf_name=settings.auth_cookie_csrf_name,
            access_path=settings.auth_cookie_access_path,
            refresh_path=settings.auth_cookie_refresh_path,
            csrf_path=settings.auth_cookie_csrf_path,
            access_same_site=same_site,
            refresh_same_site=refresh_same_site,
            secure=bool(settings.auth_cookie_secure),
            access_http_only=True,
            refresh_http_only=True,
            csrf_http_only=False,
            csrf_header_name=settings.auth_csrf_header_name,
            access_token_ttl_seconds=settings.auth_access_token_ttl_seconds,
            refresh_token_ttl_seconds=settings.auth_refresh_token_ttl_days * 86400,
            csrf_ttl_seconds=settings.auth_csrf_ttl_seconds,
            session_absolute_ttl_seconds=settings.auth_session_absolute_ttl_days * 86400,
        )

    def access_max_age(self, token_ttl_seconds: int) -> int:
        return self._bounded(min(token_ttl_seconds, self.access_token_ttl_seconds))

    def refresh_max_age(self, token_ttl_seconds: int) -> int:
        return self._bounded(min(token_ttl_seconds, self.refresh_token_ttl_seconds))

    def csrf_max_age(self) -> int:
        return self._bounded(self.csrf_ttl_seconds)

    def _bounded(self, ttl_seconds: int) -> int:
        return max(0, min(ttl_seconds, self.session_absolute_ttl_seconds))
