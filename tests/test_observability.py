from __future__ import annotations

import json
import logging
from io import StringIO
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from creator.api.dependencies import get_settings
from creator.config import Settings
from creator.infrastructure.metrics import MetricsRegistry
from creator.infrastructure.observability import (
    JsonFormatter,
    correlation_context,
    current_context,
)
from creator.main import create_app


def test_json_logs_include_correlation_and_redact_sensitive_values() -> None:
    settings = Settings(_env_file=None, app_env="test", app_name="creator-test")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(settings))
    logger = logging.getLogger("test.observability")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    request_id = uuid4()

    with correlation_context(request_id=request_id, job_id=uuid4(), correlation_id=uuid4()):
        logger.info(
            "provider_call_completed",
            extra={
                "authorization": "Bearer top-secret-token",
                "api_key": "secret-api-key",
                "password": "secret-password",
                "prompt": "private prompt text",
                "payload": {"content": "private payload"},
                "image_bytes": b"private-image-bytes",
            },
        )

    record = json.loads(stream.getvalue())
    assert record["request_id"] == str(request_id)
    assert record["environment"] == "test"
    assert record["event"] == "provider_call_completed"
    assert record["authorization"] == "[REDACTED]"
    assert record["api_key"] == "[REDACTED]"
    assert record["password"] == "[REDACTED]"
    assert record["prompt"] == "[REDACTED]"
    assert record["payload"] == "[REDACTED]"
    assert record["image_bytes"] == "[REDACTED]"
    assert "top-secret-token" not in stream.getvalue()
    assert "private prompt text" not in stream.getvalue()
    assert "private-image-bytes" not in stream.getvalue()


def test_correlation_context_is_restored_after_nested_scope() -> None:
    request_id = uuid4()
    assert current_context().request_id is None
    with correlation_context(request_id=request_id, job_id="job-1"):
        assert current_context().request_id == request_id
        assert current_context().job_id == "job-1"
    assert current_context().request_id is None
    assert current_context().job_id is None


def test_http_metrics_use_bounded_route_labels() -> None:
    registry = MetricsRegistry()
    registry.observe_http_request(
        method="GET",
        route="/api/v1/images/{id}",
        status=404,
        duration_seconds=0.012,
    )

    rendered = registry.render()
    assert "creator_http_requests_total" in rendered
    assert "creator_http_errors_total" in rendered
    assert "creator_http_request_duration_seconds_bucket" in rendered
    assert 'route="/api/v1/images/{id}"' in rendered
    assert "50000000-0000-0000-0000-000000000001" not in rendered


@pytest.mark.anyio
async def test_unexpected_http_errors_are_safe_and_correlated(caplog) -> None:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        app_env="test",
        auth_required=False,
        rate_limit_backend="memory",
    )

    @application.get("/test/unexpected/{id}")
    def unexpected(id: str) -> None:
        raise RuntimeError("password=do-not-log prompt=private")

    request_id = UUID("70000000-0000-0000-0000-000000000001")
    caplog.set_level(logging.INFO)
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/test/unexpected/55000000-0000-0000-0000-000000000001",
            headers={"X-Request-ID": str(request_id)},
        )
        metrics = await client.get("/metrics")

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == str(request_id)
    assert response.json()["error"] == {
        "code": "INTERNAL_ERROR",
        "message": "Internal server error",
    }
    assert response.json()["meta"]["request_id"] == str(request_id)
    assert "do-not-log" not in caplog.text
    assert 'route="/test/unexpected/{id}"' in metrics.text
    assert "55000000-0000-0000-0000-000000000001" not in metrics.text
