"""OpenAPI post-processing: error envelope, security schemes and rate-limit headers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from creator.config import get_settings

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
        components.setdefault("parameters", {})["RefreshCookie"] = {
            "name": settings.auth_cookie_refresh_name,
            "in": "cookie",
            "required": False,
            "description": (
                "HttpOnly refresh cookie; required for refresh and accepted by CSRF rehydration."
            ),
            "schema": {"type": "string"},
        }
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
                    "Authentication failed because credentials are missing, invalid, or expired."
                ),
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
                "x-error-codes": ["AUTHENTICATION_INVALID"],
            },
        )
        responses.setdefault(
            "LoginRejected",
            {
                "description": "Creator rejected the email and password credentials.",
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                },
                "x-error-codes": ["AUTHENTICATION_INVALID"],
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
                    if path in {"/api/v1/auth/refresh", "/api/v1/auth/csrf"}:
                        operation["security"] = []
                        operation["description"] = (
                            "Requires a valid creator_refresh cookie."
                            if path.endswith("/refresh")
                            else "Requires a valid creator_access or creator_refresh cookie."
                        )
                        operation.setdefault("parameters", []).append(
                            {"$ref": "#/components/parameters/RefreshCookie"}
                        )
                    else:
                        operation["security"] = [{"CreatorSessionCookie": []}]
                if path.startswith("/api/v1/") and "401" in operation["responses"]:
                    operation["responses"]["401"].setdefault(
                        "x-error-codes", ["AUTHENTICATION_INVALID"]
                    )
                if path.startswith("/api/v1/"):
                    operation["responses"].setdefault(
                        "401",
                        {
                            "$ref": "#/components/responses/Unauthorized",
                            "x-error-codes": ["AUTHENTICATION_INVALID"],
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
                    "creator_csrf are emitted when a session is created."
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
