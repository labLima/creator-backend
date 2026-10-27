from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from creator.config import Settings


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    request_id: UUID | None = None
    job_id: str | None = None
    correlation_id: str | None = None


_context: ContextVar[CorrelationContext | None] = ContextVar(
    "creator_observability_context",
    default=None,
)


def current_context() -> CorrelationContext:
    return _context.get() or CorrelationContext()


def resolve_request_id(value: object | None) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    return uuid4()


@contextmanager
def correlation_context(
    *,
    request_id: UUID | str | None = None,
    job_id: UUID | str | None = None,
    correlation_id: UUID | str | None = None,
) -> Iterator[CorrelationContext]:
    previous = current_context()
    context = CorrelationContext(
        request_id=_coerce_uuid(request_id) or previous.request_id,
        job_id=_coerce_text(job_id) or previous.job_id,
        correlation_id=_coerce_text(correlation_id) or previous.correlation_id,
    )
    token = _context.set(context)
    try:
        yield context
    finally:
        _context.reset(token)


def _coerce_uuid(value: UUID | str | None) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _coerce_text(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "body",
        "bytes",
        "content",
        "image_bytes",
        "password",
        "payload",
        "prompt",
        "raw",
        "refresh_token",
        "secret",
        "token",
    }
)
_SECRET_TEXT_RE = re.compile(
    r"(?i)(bearer\s+|(?:access[_-]?token|api[_-]?key|password|refresh[_-]?token|secret)\s*[=:]\s*)[^\s,;]+"
)
_JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b")


def redact_value(value: object, *, key: str | None = None) -> object:
    if key is not None and key.lower() in _SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, bytes | bytearray | memoryview):
        return "[REDACTED_BYTES]"
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple | set | frozenset):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return _JWT_RE.sub(
            "[REDACTED]",
            _SECRET_TEXT_RE.sub(r"\1[REDACTED]", value),
        )
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    """Emit one safe, structured JSON object per log line."""

    _standard_fields = frozenset(
        logging.LogRecord("observability", 0, "", 0, "", (), None).__dict__
    )

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._service = settings.app_name
        self._environment = settings.app_env

    def format(self, record: logging.LogRecord) -> str:
        context = current_context()
        event = getattr(record, "event", None) or record.getMessage()
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": redact_value(event),
            "message": redact_value(record.getMessage()),
            "service": self._service,
            "environment": self._environment,
            "request_id": str(context.request_id) if context.request_id else None,
            "job_id": context.job_id,
            "correlation_id": context.correlation_id,
        }
        for key, value in record.__dict__.items():
            if key in self._standard_fields or key.startswith("_") or key in payload:
                continue
            payload[key] = redact_value(value, key=key)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    formatter = JsonFormatter(settings)
    if not root.handlers:
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
        return
    for handler in root.handlers:
        handler.setFormatter(formatter)


def request_context_fields() -> dict[str, str | None]:
    context = current_context()
    return {
        "request_id": str(context.request_id) if context.request_id else None,
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
    }
