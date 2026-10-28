import hashlib
import hmac
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from creator.application.auth import (
    AuthConfigurationError,
    ExpiredTokenError,
    InvalidTokenError,
    principal_from_access_token,
    session_is_active,
)
from creator.application.auth_ports import AuthTokenServices
from creator.application.unit_of_work import UnitOfWork
from creator.config import Settings, get_settings
from creator.domain.auth import Principal
from creator.infrastructure.auth import auth_token_services
from creator.infrastructure.persistence.unit_of_work import get_unit_of_work
from creator.infrastructure.runtime.metrics import MetricsRegistry
from creator.infrastructure.runtime.queue import RqGenerationQueue
from creator.infrastructure.runtime.queue import get_generation_queue as get_rq_generation_queue
from creator.infrastructure.runtime.rate_limit import (
    RateLimitBackendError,
    RateLimiter,
    create_rate_limiter,
)
from creator.infrastructure.runtime.storage import create_storage_provider
from creator.repositories import UserRecord
from creator.services.ai.factory import create_llm_provider
from creator.services.ai.provider import LLMProvider
from creator.services.storage.provider import StorageConfigurationError, StorageProvider

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="CreatorLegacyBearerAuth")
logger = logging.getLogger(__name__)


def _auth_exception(
    code: str,
    message: str,
    *,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def get_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | str | None,
        Security(bearer_scheme),
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)] = None,  # type: ignore[assignment]
) -> Principal | None:
    # Keep the small direct-call API used by legacy unit tests while the HTTP
    # dependency receives a Request plus Security credentials.  The HTTP path
    # never enters this branch.
    if isinstance(credentials, Settings) and not isinstance(request, Request):
        legacy_credentials = request
        request = None
        settings = credentials
        credentials = legacy_credentials
    request_obj = request if isinstance(request, Request) else None
    bearer = _bearer_token(credentials) if settings.auth_legacy_bearer_enabled else None
    cookie = (
        request_obj.cookies.get(settings.auth_cookie_access_name)
        if request_obj is not None and settings.auth_cookie_sessions_enabled
        else None
    )
    if bearer and cookie:
        # During the one-release migration window an explicit legacy Bearer
        # credential remains authoritative for clients that still retain a
        # browser cookie from another session.
        bearer_principal = _decode_principal(bearer, settings, token_services)
        if request_obj is not None:
            request_obj.state.auth_source = "bearer"
        return bearer_principal
    token = bearer or cookie
    if token is None:
        if settings.auth_required:
            raise _invalid_auth_exception()
        return None

    try:
        principal = principal_from_access_token(token, settings, token_services=token_services)
        if request_obj is not None:
            request_obj.state.auth_source = "bearer" if bearer else "cookie"
        return principal
    except AuthConfigurationError as error:
        if not settings.auth_required:
            return None
        raise _auth_exception(
            "AUTHENTICATION_MISCONFIGURED",
            "Authentication is not configured",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from error
    except (ExpiredTokenError, InvalidTokenError) as error:
        raise _invalid_auth_exception() from error


def get_optional_principal(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)] = None,  # type: ignore[assignment]
) -> Principal | None:
    """Validate a supplied token without making authentication mandatory.

    The global rate-limit dependency must be able to rate-limit public Auth routes
    by IP before the endpoint's own authentication requirements are evaluated.
    """
    bearer = request.headers.get("Authorization") if settings.auth_legacy_bearer_enabled else None
    cookie = (
        request.cookies.get(settings.auth_cookie_access_name)
        if settings.auth_cookie_sessions_enabled
        else None
    )
    if bearer and cookie:
        bearer_token = _bearer_token(bearer)
        if bearer_token is None:
            return None
        try:
            bearer_principal = principal_from_access_token(
                bearer_token, settings, token_services=token_services
            )
        except (AuthConfigurationError, ExpiredTokenError, InvalidTokenError):
            return None
        return bearer_principal
    token = bearer or cookie
    if not token:
        return None

    bearer_token = _bearer_token(token) if bearer else token
    if bearer_token is None:
        return None
    try:
        principal = principal_from_access_token(
            bearer_token, settings, token_services=token_services
        )
        request.state.auth_source = "bearer" if bearer else "cookie"
        return principal
    except AuthConfigurationError as error:
        if not settings.auth_required:
            return None
        raise _auth_exception(
            "AUTHENTICATION_MISCONFIGURED",
            "Authentication is not configured",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from error
    except (ExpiredTokenError, InvalidTokenError) as error:
        if not bearer:
            return None
        raise _invalid_auth_exception() from error


def get_uow(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UnitOfWork:
    return unit_of_work


def get_current_user(
    principal: Annotated[Principal | None, Depends(get_principal)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserRecord:
    if principal is None:
        raise _invalid_auth_exception()
    try:
        user_id = UUID(principal.subject)
        session_id = UUID(principal.session_id or "")
    except ValueError as error:
        raise _invalid_auth_exception() from error
    if not session_is_active(unit_of_work=unit_of_work, session_id=session_id):
        raise _invalid_auth_exception()
    existing = unit_of_work.users.get_by_id(user_id, include_deleted=True)
    if existing is None or existing.deleted_at is not None:
        raise _invalid_auth_exception()
    return existing


def get_optional_current_user(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserRecord | None:
    if principal is None:
        return None
    try:
        user_id = UUID(principal.subject)
        session_id = UUID(principal.session_id or "")
    except ValueError:
        return None
    if not session_is_active(unit_of_work=unit_of_work, session_id=session_id):
        return None
    existing = unit_of_work.users.get_by_id(user_id, include_deleted=True)
    if existing is None or existing.deleted_at is not None:
        return None
    return existing


def get_llm_provider(
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> LLMProvider:
    return create_llm_provider(settings)


def get_storage_provider(
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> StorageProvider:
    try:
        return create_storage_provider(settings)
    except StorageConfigurationError as error:
        raise _auth_exception(
            "STORAGE_MISCONFIGURED",
            "Storage is not configured",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from error


def get_generation_queue() -> RqGenerationQueue:
    return get_rq_generation_queue()


def get_metrics_registry(request: Request) -> MetricsRegistry:
    registry = getattr(request.app.state, "metrics_registry", None)
    if not isinstance(registry, MetricsRegistry):
        registry = MetricsRegistry()
        request.app.state.metrics_registry = registry
    return registry


def get_rate_limiter(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
    metrics: Annotated[MetricsRegistry, Depends(get_metrics_registry)] = None,  # type: ignore[assignment]
) -> RateLimiter:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if not isinstance(limiter, RateLimiter):
        limiter = create_rate_limiter(settings, metrics)
        request.app.state.rate_limiter = limiter
    return limiter


GENERATION_RATE_LIMIT_ENDPOINTS = frozenset(
    {
        "POST /api/v1/content/generate",
        "POST /api/v1/content/improve",
        "POST /api/v1/images/generate",
        "POST /api/v1/images/{id}/regenerate",
        "POST /api/v1/generations/image-workflows",
        "POST /api/v1/generations/image-workflows/{id}/decision",
    }
)
AUTH_RATE_LIMIT_ENDPOINTS = frozenset(
    {
        "POST /api/v1/auth/login",
        "POST /api/v1/auth/signup",
        "POST /api/v1/auth/refresh",
    }
)
ROUTE_ALIASES = {
    "GET /api/v1/content": "GET /api/v1/contents",
    "GET /api/v1/content/{id}": "GET /api/v1/contents/{id}",
    "DELETE /api/v1/content/{id}": "DELETE /api/v1/contents/{id}",
}


def enforce_rate_limit(
    request: Request,
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    path = request.url.path
    if not path.startswith("/api/v1/"):
        return

    route = request.scope.get("route")
    route_path = getattr(route, "path", path)
    route_key = f"{request.method.upper()} {route_path}"
    endpoint = ROUTE_ALIASES.get(route_key, route_key)
    rate_class = "generation" if endpoint in GENERATION_RATE_LIMIT_ENDPOINTS else "cheap"

    if endpoint in AUTH_RATE_LIMIT_ENDPOINTS:
        client_host = request.client.host if request.client else "unknown"
        identity = f"ip:{client_host}"
    elif principal is not None:
        identity = f"principal:{principal.subject}"
    else:
        # The endpoint's authentication dependency remains authoritative.
        return

    try:
        decision = limiter.check(
            rate_class=rate_class,
            endpoint=endpoint,
            identity=identity,
        )
    except RateLimitBackendError as error:
        if rate_class == "cheap":
            logger.warning(
                "Rate limiter unavailable; allowing cheap request",
                extra={"rate_limit_class": rate_class, "rate_limit_endpoint": endpoint},
            )
            return
        logger.error(
            "Rate limiter unavailable; rejecting generation request",
            extra={"rate_limit_class": rate_class, "rate_limit_endpoint": endpoint},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "RATE_LIMITER_UNAVAILABLE",
                "message": "Rate limiter is temporarily unavailable",
            },
            headers={"Retry-After": "1"},
        ) from error

    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded for this endpoint",
            },
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "RateLimit-Limit": str(limiter.limit),
                "RateLimit-Remaining": str(decision.remaining),
                "RateLimit-Reset": str(decision.reset_seconds),
            },
        )


def enforce_cookie_security(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)],
) -> None:
    if request.method.upper() in {"GET", "HEAD", "OPTIONS"} or not request.url.path.startswith(
        "/api/v1/"
    ):
        return
    if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/signup"}:
        return
    if not settings.auth_cookie_sessions_enabled:
        return

    has_session_cookie = any(
        request.cookies.get(name)
        for name in (settings.auth_cookie_access_name, settings.auth_cookie_refresh_name)
    )
    if not has_session_cookie:
        return
    if settings.auth_legacy_bearer_enabled and request.headers.get("Authorization"):
        return

    origin = request.headers.get("origin")
    expected_origin = f"{request.url.scheme}://{request.url.netloc}"
    allowed_origins = set(settings.auth_cors_origins) or {expected_origin}
    if origin is None or origin == "null" or origin not in allowed_origins:
        raise _auth_exception(
            "ORIGIN_NOT_ALLOWED",
            "Request origin is not allowed",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    session_id: UUID | None = None
    access = request.cookies.get(settings.auth_cookie_access_name)
    if access:
        try:
            session_id = UUID(
                principal_from_access_token(
                    access, settings, token_services=token_services
                ).session_id
                or ""
            )
        except (AuthConfigurationError, ExpiredTokenError, InvalidTokenError, ValueError):
            session_id = None
    if session_id is None:
        refresh = request.cookies.get(settings.auth_cookie_refresh_name)
        if refresh:
            record = unit_of_work.auth_sessions.get_by_refresh_hash(_refresh_hash(refresh))
            session_id = record.id if record is not None else None
    csrf_cookie = request.cookies.get(settings.auth_cookie_csrf_name)
    csrf_header = request.headers.get(settings.auth_csrf_header_name)
    if not csrf_cookie or not csrf_header:
        raise _auth_exception(
            "CSRF_TOKEN_MISSING",
            "CSRF token is required",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if session_id is None or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise _auth_exception(
            "CSRF_TOKEN_INVALID",
            "CSRF token is invalid",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if not token_services.csrf.verify(token=csrf_header, session_id=session_id, settings=settings):
        raise _auth_exception(
            "CSRF_TOKEN_INVALID",
            "CSRF token is invalid",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def _invalid_auth_exception() -> HTTPException:
    return _auth_exception("AUTHENTICATION_INVALID", "Authentication failed")


def _bearer_token(credentials: HTTPAuthorizationCredentials | str | None) -> str | None:
    if credentials is None:
        return None
    if isinstance(credentials, str):
        scheme, _, token = credentials.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise _invalid_auth_exception()
        return token
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _invalid_auth_exception()
    return credentials.credentials


def _decode_principal(
    token: str, settings: Settings, token_services: AuthTokenServices
) -> Principal:
    try:
        return principal_from_access_token(token, settings, token_services=token_services)
    except (AuthConfigurationError, ExpiredTokenError, InvalidTokenError) as error:
        raise _invalid_auth_exception() from error


def _refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _display_name_from_claims(principal: Principal) -> str | None:
    user_metadata = principal.claims.get("user_metadata")
    if not isinstance(user_metadata, dict):
        return None
    for key in ("display_name", "full_name", "name"):
        value = user_metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None
