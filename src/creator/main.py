from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from creator.api.dependencies import (
    enforce_cookie_security,
    enforce_rate_limit,
)
from creator.api.responses import (
    error_response,
    success_response,
)
from creator.api.router import api_router
from creator.application.unit_of_work import UnitOfWork
from creator.config import get_settings
from creator.domain.auth import Principal
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.runtime.metrics import MetricsRegistry
from creator.infrastructure.runtime.observability import (
    configure_logging,
    correlation_context,
    resolve_request_id,
)
from creator.repositories import (
    UserRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
)

OPENAPI_TAGS = [
    {"name": "System", "description": "Health, liveness and operational endpoints."},
    {"name": "Auth", "description": "Authentication and signup endpoints."},
    {"name": "Users", "description": "User profile and administration endpoints."},
    {"name": "Settings", "description": "Authenticated Principal settings endpoints."},
    {"name": "Workspaces", "description": "Workspace lifecycle endpoints."},
    {"name": "Brands", "description": "Brand and Brand Settings endpoints."},
    {"name": "Projects", "description": "Project endpoints."},
    {"name": "Contents", "description": "Content CRUD and content workflow endpoints."},
    {"name": "Generations", "description": "Generation lifecycle endpoints."},
    {"name": "Assets", "description": "Asset metadata endpoints."},
    {"name": "Images", "description": "Image generation and retrieval endpoints."},
    {"name": "Campaigns", "description": "Campaign lifecycle endpoints."},
    {"name": "Personas", "description": "Audience persona endpoints."},
    {"name": "Planning", "description": "Content planning endpoints."},
    {"name": "Post Structures", "description": "Post structure endpoints."},
    {"name": "Brand Assets", "description": "Brand asset endpoints."},
    {"name": "Notifications", "description": "Principal notification settings and devices."},
    {"name": "Billing", "description": "Billing plan administration endpoints."},
]

logger = logging.getLogger(__name__)


def _bootstrap_signup_workspace(
    *,
    unit_of_work: UnitOfWork,
    principal: Principal,
    workspace_name: str,
) -> tuple[UserRecord, WorkspaceRecord, WorkspaceMembershipRecord]:
    existing = unit_of_work.users.get_by_external_id(principal.subject, include_deleted=True)
    if existing is not None and existing.deleted_at is not None:
        raise EntityNotFoundError("User not found")
    user = existing or unit_of_work.users.add(
        external_id=principal.subject,
        email=principal.email,
        display_name=None,
    )
    created = unit_of_work.workspaces.create_for_user(
        user_id=user.id,
        name=workspace_name,
    )
    unit_of_work.commit()
    return user, created.workspace, created.membership


def _install_rate_limit_openapi(application: FastAPI) -> None:
    original_openapi = application.openapi

    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema

        settings = get_settings()
        schema = original_openapi()
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas.setdefault(
            "ErrorResponse",
            {
                "type": "object",
                "required": ["success", "error", "meta"],
                "properties": {
                    "success": {"const": False},
                    "error": {
                        "type": "object",
                        "required": ["code", "message"],
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                        },
                    },
                    "meta": {
                        "type": "object",
                        "required": ["request_id"],
                        "properties": {"request_id": {"type": "string", "format": "uuid"}},
                    },
                },
            },
        )
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["CreatorSessionCookie"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.auth_cookie_access_name,
            "description": (
                "HttpOnly Creator access cookie; mutating requests also require X-CSRF-Token."
            ),
        }
        security_schemes["CreatorRefreshCookie"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.auth_cookie_refresh_name,
            "description": "HttpOnly Creator refresh cookie used only for session rotation.",
        }
        if settings.auth_legacy_bearer_enabled:
            security_schemes["CreatorLegacyBearerAuth"] = {
                "type": "http",
                "scheme": "bearer",
                "description": (
                    "Legacy Bearer accepted only when AUTH_LEGACY_BEARER_ENABLED=true."
                ),
            }
        else:
            security_schemes.pop("CreatorLegacyBearerAuth", None)
        responses = components.setdefault("responses", {})
        headers = components.setdefault("headers", {})
        headers.setdefault(
            "RequestId",
            {
                "description": "Request identifier used to correlate the response and logs.",
                "schema": {"type": "string", "format": "uuid"},
            },
        )
        headers.setdefault(
            "NoStore",
            {
                "description": "Prevents caches from storing authentication responses.",
                "schema": {"type": "string", "const": "no-store"},
            },
        )
        responses.setdefault(
            "InternalServerError",
            {
                "description": "Unexpected server failure with a safe error envelope.",
                "headers": {"X-Request-ID": {"$ref": "#/components/headers/RequestId"}},
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
        )
        responses.setdefault(
            "RateLimitExceeded",
            {
                "description": "The caller exceeded the configured per-endpoint rate limit.",
                "headers": {
                    "Retry-After": {"schema": {"type": "integer", "minimum": 1}},
                    "RateLimit-Limit": {"schema": {"type": "integer", "minimum": 1}},
                    "RateLimit-Remaining": {"schema": {"type": "integer", "minimum": 0}},
                    "RateLimit-Reset": {"schema": {"type": "integer", "minimum": 1}},
                },
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
        )
        responses.setdefault(
            "RateLimiterUnavailable",
            {
                "description": "The distributed rate limiter is unavailable.",
                "headers": {"Retry-After": {"schema": {"type": "integer", "minimum": 1}}},
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
            },
        )
        responses.setdefault(
            "Unauthorized",
            {
                "description": (
                    "Authentication failed because credentials are missing, invalid, expired, "
                    "or because the Bearer and cookie credentials identify different Principals "
                    "(AUTH_AMBIGUOUS)."
                ),
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
                "x-error-codes": ["AUTHENTICATION_INVALID", "AUTH_AMBIGUOUS"],
            },
        )
        responses.setdefault(
            "LoginRejected",
            {
                "description": (
                    "Creator rejected the email and password credentials or the supplied "
                    "Bearer and cookie credentials are ambiguous (AUTH_AMBIGUOUS)."
                ),
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
                "x-error-codes": ["AUTHENTICATION_INVALID", "AUTH_AMBIGUOUS"],
            },
        )
        responses.setdefault(
            "CsrfRejected",
            {
                "description": "CSRF token is missing or invalid, or the Origin is not allowed.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
                "x-error-codes": [
                    "CSRF_TOKEN_MISSING",
                    "CSRF_TOKEN_INVALID",
                    "ORIGIN_NOT_ALLOWED",
                ],
            },
        )

        generation_paths = {
            "/api/v1/content/generate",
            "/api/v1/content/improve",
            "/api/v1/images/generate",
            "/api/v1/images/{id}/regenerate",
        }
        for path, path_item in schema.get("paths", {}).items():
            for _method, operation in path_item.items():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                if path.startswith("/api/v1/") and path not in {
                    "/api/v1/auth/login",
                    "/api/v1/auth/signup",
                }:
                    if path == "/api/v1/auth/refresh":
                        operation["security"] = [{"CreatorRefreshCookie": []}]
                    elif path == "/api/v1/auth/csrf":
                        operation["security"] = [
                            {"CreatorSessionCookie": []},
                            {"CreatorRefreshCookie": []},
                        ]
                        if settings.auth_legacy_bearer_enabled:
                            operation["security"].append({"CreatorLegacyBearerAuth": []})
                    else:
                        operation["security"] = [{"CreatorSessionCookie": []}]
                        if settings.auth_legacy_bearer_enabled:
                            operation["security"].append({"CreatorLegacyBearerAuth": []})
                if path.startswith("/api/v1/") and "401" in operation["responses"]:
                    operation["responses"]["401"].setdefault(
                        "x-error-codes", ["AUTHENTICATION_INVALID", "AUTH_AMBIGUOUS"]
                    )
                if path.startswith("/api/v1/"):
                    operation["responses"].setdefault(
                        "401",
                        {
                            "$ref": "#/components/responses/Unauthorized",
                            "x-error-codes": ["AUTHENTICATION_INVALID", "AUTH_AMBIGUOUS"],
                        },
                    )
                    if path == "/api/v1/auth/refresh":
                        operation["responses"]["401"]["x-error-codes"] = ["INVALID_REFRESH_TOKEN"]
                    operation["responses"].setdefault(
                        "429",
                        {"$ref": "#/components/responses/RateLimitExceeded"},
                    )
                    if path in generation_paths:
                        operation["responses"].setdefault(
                            "503", {"$ref": "#/components/responses/RateLimiterUnavailable"}
                        )
                if (
                    path in {"/api/v1/auth/refresh", "/api/v1/auth/logout"}
                    and _method.lower() == "post"
                ):
                    operation["responses"].setdefault(
                        "403",
                        {
                            "$ref": "#/components/responses/CsrfRejected",
                            "x-error-codes": [
                                "CSRF_TOKEN_MISSING",
                                "CSRF_TOKEN_INVALID",
                                "ORIGIN_NOT_ALLOWED",
                            ],
                        },
                    )
                if path == "/api/v1/auth/refresh" and _method.lower() == "post":
                    operation["responses"].setdefault(
                        "409",
                        {
                            "$ref": "#/components/responses/RefreshInProgress",
                            "x-error-codes": ["REFRESH_IN_PROGRESS"],
                        },
                    )
                if (
                    path
                    in {
                        "/api/v1/auth/csrf",
                        "/api/v1/auth/refresh",
                        "/api/v1/auth/logout",
                    }
                    and "200" in operation["responses"]
                ):
                    success = operation["responses"]["200"]
                    response_headers = success.setdefault("headers", {})
                    response_headers["Cache-Control"] = {"$ref": "#/components/headers/NoStore"}
                    if path in {"/api/v1/auth/refresh", "/api/v1/auth/logout"}:
                        response_headers["Set-Cookie"] = {
                            "description": "Creator session cookies are set or cleared.",
                            "schema": {"type": "string"},
                        }
                operation["responses"].setdefault(
                    "500", {"$ref": "#/components/responses/InternalServerError"}
                )
                for response in operation["responses"].values():
                    if isinstance(response, dict) and "$ref" not in response:
                        response.setdefault(
                            "headers",
                            {"X-Request-ID": {"$ref": "#/components/headers/RequestId"}},
                        )

        schemas = components.setdefault("schemas", {})
        schemas["AuthPrincipal"] = {
            "type": "object",
            "required": ["subject"],
            "properties": {
                "subject": {"type": "string", "minLength": 1},
                "email": {"type": ["string", "null"], "format": "email"},
                "role": {"type": ["string", "null"]},
            },
        }
        schemas["AuthSession"] = {
            "type": "object",
            "required": [
                "token_type",
                "expires_in",
                "refresh_expires_in",
                "csrf_token",
                "principal",
                "provider",
                "metadata",
            ],
            "properties": {
                "token_type": {"type": "string"},
                "expires_in": {"type": "integer", "minimum": 1},
                "refresh_expires_in": {"type": "integer", "minimum": 1},
                "csrf_token": {"type": "string", "readOnly": True},
                "principal": {"$ref": "#/components/schemas/AuthPrincipal"},
                "provider": {"type": "string", "const": "local"},
                "metadata": {"type": "object", "additionalProperties": True},
                "access_token": {
                    "type": "string",
                    "deprecated": True,
                    "description": (
                        "Legacy transition field, returned only while "
                        "AUTH_TOKEN_BODY_ENABLED=true. Prefer the HttpOnly creator_access cookie."
                    ),
                },
                "refresh_token": {
                    "type": "string",
                    "deprecated": True,
                    "description": (
                        "Legacy transition field, returned only while "
                        "AUTH_TOKEN_BODY_ENABLED=true. Prefer the HttpOnly creator_refresh cookie."
                    ),
                },
            },
        }
        schemas["AuthLoginResponse"] = {
            "type": "object",
            "required": ["success", "data", "meta"],
            "properties": {
                "success": {"const": True},
                "data": {"$ref": "#/components/schemas/AuthSession"},
                "meta": {
                    "type": "object",
                    "required": ["request_id"],
                    "properties": {"request_id": {"type": "string", "format": "uuid"}},
                },
            },
        }
        schemas["AuthSignupResult"] = {
            "type": "object",
            "required": [
                "principal",
                "session",
                "workspace",
                "membership",
                "confirmation_required",
                "provider",
                "metadata",
            ],
            "properties": {
                "principal": {"$ref": "#/components/schemas/AuthPrincipal"},
                "session": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/AuthSession"},
                        {"type": "null"},
                    ]
                },
                "workspace": {"type": "object", "additionalProperties": True},
                "membership": {"type": "object", "additionalProperties": True},
                "confirmation_required": {"type": "boolean"},
                "provider": {"type": "string", "const": "local"},
                "metadata": {"type": "object", "additionalProperties": True},
            },
        }
        schemas["AuthSignupResponse"] = {
            "type": "object",
            "required": ["success", "data", "meta"],
            "properties": {
                "success": {"const": True},
                "data": {"$ref": "#/components/schemas/AuthSignupResult"},
                "meta": {
                    "type": "object",
                    "required": ["request_id"],
                    "properties": {"request_id": {"type": "string", "format": "uuid"}},
                },
            },
        }

        for path, status_code, response_schema in (
            ("/api/v1/auth/login", "200", "AuthLoginResponse"),
            ("/api/v1/auth/signup", "201", "AuthSignupResponse"),
        ):
            operation_responses = schema["paths"][path]["post"]["responses"]
            success = operation_responses[status_code]
            success.setdefault("content", {}).setdefault("application/json", {})["schema"] = {
                "$ref": f"#/components/schemas/{response_schema}"
            }
            success.setdefault("headers", {})["Set-Cookie"] = {
                "description": (
                    "Separate Set-Cookie headers for creator_access, creator_refresh and "
                    "creator_csrf are emitted when cookie sessions are enabled."
                ),
                "schema": {"type": "string"},
            }
            for response in operation_responses.values():
                if isinstance(response, dict):
                    response.setdefault("headers", {})["Cache-Control"] = {
                        "$ref": "#/components/headers/NoStore"
                    }

        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]


def _normalized_route(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else "__unmatched__"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(
        title="Creator API",
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        dependencies=[Depends(enforce_rate_limit), Depends(enforce_cookie_security)],
    )
    if settings.auth_cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.auth_cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-CSRF-Token",
                "Idempotency-Key",
                "X-Request-ID",
            ],
            expose_headers=[
                "X-Request-ID",
                "RateLimit-Limit",
                "RateLimit-Remaining",
                "RateLimit-Reset",
                "Retry-After",
            ],
        )
    application.include_router(api_router)
    _install_rate_limit_openapi(application)

    @application.middleware("http")
    async def observability_middleware(request: Request, call_next: Any) -> Response:
        request_id = resolve_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        registry = getattr(application.state, "metrics_registry", None)
        if not isinstance(registry, MetricsRegistry):
            registry = MetricsRegistry()
            application.state.metrics_registry = registry
        started_at = time.perf_counter()
        response: Response | None = None
        status_code = 500
        with correlation_context(request_id=request_id):
            try:
                response = await call_next(request)
                status_code = response.status_code
                return response
            finally:
                duration_seconds = time.perf_counter() - started_at
                route = _normalized_route(request)
                if request.url.path != "/metrics":
                    registry.observe_http_request(
                        method=request.method.upper(),
                        route=route,
                        status=status_code,
                        duration_seconds=duration_seconds,
                    )
                logger.info(
                    "http_request_completed",
                    extra={
                        "method": request.method.upper(),
                        "route": route,
                        "status": status_code,
                        "duration_ms": int(duration_seconds * 1000),
                    },
                )
                if response is not None:
                    response.headers["X-Request-ID"] = str(request_id)
                    if request.url.path in {
                        "/api/v1/auth/login",
                        "/api/v1/auth/signup",
                    }:
                        response.headers["Cache-Control"] = "no-store"

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code", "HTTP_ERROR"))
            message = str(detail.get("message", "Request failed"))
        else:
            code = "HTTP_ERROR"
            message = "Request failed"
        return error_response(
            code,
            message,
            status_code=exc.status_code,
            request=request,
            headers=exc.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            "VALIDATION_FAILED",
            "Request validation failed",
            status_code=422,
            request=request,
        )

    @application.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "http_unhandled_exception",
            extra={"exception_type": exc.__class__.__name__, "status": 500},
        )
        return error_response(
            "INTERNAL_ERROR",
            "Internal server error",
            status_code=500,
            request=request,
        )

    return application


app = create_app()

__all__ = ["app", "create_app", "error_response", "success_response"]
