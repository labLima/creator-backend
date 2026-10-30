from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from creator.infrastructure.runtime.observability import resolve_request_id
from creator.repositories.common import Page

ResponseHeaders = Mapping[str, str] | Sequence[tuple[str, str]]


def request_id_for(request: Request | None = None) -> UUID:
    if request is None:
        return uuid4()
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, UUID):
        return existing
    request_id = resolve_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    return request_id


def _header_items(headers: ResponseHeaders | None) -> Sequence[tuple[str, str]]:
    if headers is None:
        return ()
    if isinstance(headers, Mapping):
        return tuple(headers.items())
    return headers


def success_response(
    data: dict[str, Any],
    request: Request | None = None,
    *,
    status_code: int = 200,
    headers: ResponseHeaders | None = None,
) -> JSONResponse:
    request_id = request_id_for(request)
    response = JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "meta": {"request_id": str(request_id)}},
        headers={"X-Request-ID": str(request_id)},
    )
    for name, value in _header_items(headers):
        if name.lower() != "x-request-id":
            response.headers.append(name, value)
    return response


def _json_response(
    payload: dict[str, Any],
    request_id: UUID,
    status_code: int,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    response_headers = {"X-Request-ID": str(request_id)}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers=response_headers,
    )


def error_response(
    code: str,
    message: str,
    *,
    status_code: int,
    request: Request | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_for(request)
    return _json_response(
        {
            "success": False,
            "error": {"code": code, "message": message},
            "meta": {"request_id": str(request_id)},
        },
        request_id,
        status_code,
        headers,
    )


def page_payload(page: Page[Any], serializer: Any) -> dict[str, Any]:
    return {
        "items": [serializer(item) for item in page.items],
        "pagination": {
            "page": page.page,
            "limit": page.limit,
            "total": page.total,
        },
    }
