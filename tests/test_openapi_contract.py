from __future__ import annotations

from pathlib import Path

import yaml

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations(path_item: dict[str, object]) -> set[str]:
    return {method for method in path_item if method in HTTP_METHODS}


def test_static_openapi_matches_application_routes() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()

    assert set(static["paths"]) == set(generated["paths"])
    for path, generated_item in generated["paths"].items():
        assert _operations(static["paths"][path]) == _operations(generated_item), path


def test_static_openapi_declares_creator_cookie_security() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))

    assert static["components"]["securitySchemes"]["CreatorSessionCookie"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": "creator_access",
        "description": (
            "HttpOnly Creator access cookie; mutating requests also require X-CSRF-Token."
        ),
    }
    assert "CreatorBearerAuth" not in static["components"]["securitySchemes"]
    assert "AuthRefreshRequest" not in static["components"]["schemas"]
    assert "requestBody" not in static["paths"]["/api/v1/auth/refresh"]["post"]
    for path, item in static["paths"].items():
        if not path.startswith("/api/v1/") or path in PUBLIC_AUTH_PATHS:
            continue
        for method in _operations(item):
            assert item[method].get("security") == [{"CreatorSessionCookie": []}], (method, path)


def test_auth_openapi_documents_cookie_headers_and_optional_legacy_tokens() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()
    static_session = static["components"]["schemas"]["AuthSession"]
    generated_session = generated["components"]["schemas"]["AuthSession"]

    for token_name in ("access_token", "refresh_token"):
        assert token_name not in static_session["required"]
        assert token_name not in generated_session["required"]
        assert static_session["properties"][token_name]["deprecated"] is True
        assert generated_session["properties"][token_name]["deprecated"] is True

    for path, success_code in (
        ("/api/v1/auth/login", "200"),
        ("/api/v1/auth/signup", "201"),
    ):
        static_responses = static["paths"][path]["post"]["responses"]
        generated_responses = generated["paths"][path]["post"]["responses"]
        static_success_headers = static_responses[success_code]["headers"]
        generated_success_headers = generated_responses[success_code]["headers"]
        assert {"Set-Cookie", "Cache-Control"} <= set(static_success_headers)
        assert {"Set-Cookie", "Cache-Control"} <= set(generated_success_headers)
        for status_code, response in static_responses.items():
            assert "Cache-Control" in response["headers"], (path, status_code)
        for response in generated_responses.values():
            assert "Cache-Control" in response["headers"]

    assert (
        static["components"]["headers"]["NoStore"] == generated["components"]["headers"]["NoStore"]
    )


def test_workflow_acceptance_does_not_document_redis_availability_errors() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()
    paths = (
        "/api/v1/generations/image-workflows",
        "/api/v1/generations/image-workflows/{id}/decision",
    )
    for path in paths:
        assert "503" not in static["paths"][path]["post"]["responses"]
        assert "503" not in generated["paths"][path]["post"]["responses"]
