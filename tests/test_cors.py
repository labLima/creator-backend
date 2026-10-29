from __future__ import annotations

import pytest
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

import creator.main as main_module
from creator.config import Settings


def _app_with_cors(monkeypatch: pytest.MonkeyPatch, origins: list[str]):
    settings = Settings(_env_file=None, auth_cors_origins=origins)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    return main_module.create_app()


@pytest.mark.parametrize(
    "origins",
    [
        ["*"],
        ["https://*.example.com"],
        ["null"],
        ["https://spa.example/path"],
        ["https://spa.example?mode=app"],
        ["https://spa.example/#section"],
        ["https://user:secret@spa.example"],
        ["https://spa.example\\attacker.example"],
        ["https://spa%00.example"],
        ["ftp://spa.example"],
        ["https://spa.example:"],
        ["https://spa.example:70000"],
    ],
)
def test_cors_allowlist_rejects_non_exact_origins(origins: list[str]) -> None:
    with pytest.raises(ValueError, match="AUTH_CORS_ORIGINS"):
        Settings(_env_file=None, auth_cors_origins=origins)


def test_cors_allowlist_accepts_exact_http_origins() -> None:
    settings = Settings(
        _env_file=None,
        auth_cors_origins=["https://app.example.com", "http://localhost:3000"],
    )

    assert settings.auth_cors_origins == ["https://app.example.com", "http://localhost:3000"]


@pytest.mark.anyio
async def test_allowed_cors_preflight_includes_credentials_and_explicit_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = "https://app.example.com"
    app = _app_with_cors(monkeypatch, [origin])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://api.example.com"
    ) as client:
        response = await client.options(
            "/api/v1/auth/logout",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,content-type,x-csrf-token,idempotency-key,x-request-id"
                ),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    allowed_methods = {
        method.strip() for method in response.headers["access-control-allow-methods"].split(",")
    }
    assert {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"} <= allowed_methods
    allowed_headers = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }
    assert {
        "authorization",
        "content-type",
        "x-csrf-token",
        "idempotency-key",
        "x-request-id",
    } <= allowed_headers


@pytest.mark.anyio
async def test_disallowed_cors_preflight_is_rejected_without_allow_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_with_cors(monkeypatch, ["https://app.example.com"])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://api.example.com"
    ) as client:
        response = await client.options(
            "/api/v1/auth/logout",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-CSRF-Token",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.anyio
async def test_cors_exposes_creator_response_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    origin = "https://app.example.com"
    app = _app_with_cors(monkeypatch, [origin])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://api.example.com"
    ) as client:
        response = await client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    exposed = {
        header.strip().lower()
        for header in response.headers["access-control-expose-headers"].split(",")
    }
    assert {
        "x-request-id",
        "ratelimit-limit",
        "ratelimit-remaining",
        "ratelimit-reset",
        "retry-after",
    } <= exposed


@pytest.mark.anyio
async def test_empty_allowlist_keeps_cors_disabled_for_same_origin_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_with_cors(monkeypatch, [])
    assert not any(middleware.cls is CORSMiddleware for middleware in app.user_middleware)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://api.example.com"
    ) as client:
        response = await client.get("/health", headers={"Origin": "http://api.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
