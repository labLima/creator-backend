"""HTTP routes for the system capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from creator.api.dependencies import (
    get_metrics_registry,
)
from creator.api.responses import (
    success_response,
)
from creator.infrastructure.runtime.metrics import MetricsRegistry

router = APIRouter()


@router.get("/health", tags=["System"])
async def health(request: Request) -> JSONResponse:
    return success_response({"status": "ok"}, request)


@router.get("/health/live", tags=["System"])
async def live_health(request: Request) -> JSONResponse:
    return success_response({"status": "ok"}, request)


@router.get("/metrics", include_in_schema=True, tags=["System"])
def metrics(
    registry: Annotated[MetricsRegistry, Depends(get_metrics_registry)],
) -> PlainTextResponse:
    # Keep this endpoint outside /api/v1 so observability cannot consume user quota.
    return PlainTextResponse(registry.render(), media_type=registry.content_type)
