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
from creator.api.openapi import OPENAPI_TAGS, _install_rate_limit_openapi
from creator.api.responses import (
    error_response,
    success_response,
)
from creator.api.router import api_router
from creator.config import get_settings
from creator.infrastructure.runtime.metrics import MetricsRegistry
from creator.infrastructure.runtime.observability import (
    configure_logging,
    correlation_context,
    resolve_request_id,
)

logger = logging.getLogger(__name__)


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
