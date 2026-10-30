from __future__ import annotations

from pathlib import Path

import yaml

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/signup"}
REFRESH_COOKIE_PATHS = {"/api/v1/auth/refresh", "/api/v1/auth/csrf"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations(path_item: dict[str, object]) -> set[str]:
    return {method for method in path_item if method in HTTP_METHODS}


def test_static_openapi_matches_application_routes() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()

    assert set(static["paths"]) == set(generated["paths"])
    for path, generated_item in generated["paths"].items():
        assert _operations(static["paths"][path]) == _operations(generated_item), path


def test_static_and_generated_openapi_declare_cookie_security() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()
    expected_scheme = {
        "type": "apiKey",
        "in": "cookie",
        "name": "creator_access",
        "description": (
            "HttpOnly Creator access cookie; mutating requests also require X-CSRF-Token."
        ),
    }
    assert static["components"]["securitySchemes"] == {"CreatorSessionCookie": expected_scheme}
    assert generated["components"]["securitySchemes"] == {"CreatorSessionCookie": expected_scheme}
    assert (
        static["components"]["parameters"]["RefreshCookie"]
        == generated["components"]["parameters"]["RefreshCookie"]
    )
    for path, item in static["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method in _operations(item):
            operation = item[method]
            generated_operation = generated["paths"][path][method]
            if path in PUBLIC_AUTH_PATHS | REFRESH_COOKIE_PATHS:
                expected_security = []
            else:
                expected_security = [{"CreatorSessionCookie": []}]
            assert operation.get("security", []) == expected_security, (method, path)
            assert generated_operation.get("security", []) == expected_security, (method, path)
            if path in REFRESH_COOKIE_PATHS:
                ref = {"$ref": "#/components/parameters/RefreshCookie"}
                assert ref in operation.get("parameters", []), (method, path)
                assert ref in generated_operation.get("parameters", []), (method, path)
            assert "AUTH_AMBIGUOUS" not in operation["responses"]["401"].get("x-error-codes", [])
            assert "AUTH_AMBIGUOUS" not in generated_operation["responses"]["401"].get(
                "x-error-codes", []
            )


def test_auth_openapi_documents_cookie_headers_and_no_tokens() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()
    static_session = static["components"]["schemas"]["AuthSession"]
    generated_session = generated["components"]["schemas"]["AuthSession"]

    expected_session_fields = {"csrf_token", "expires_in", "refresh_expires_in"}
    for document, session in ((static, static_session), (generated, generated_session)):
        assert expected_session_fields <= set(session["required"])
        assert not {"access_token", "refresh_token"} & set(session["properties"])
        assert "AuthRefreshRequest" not in document["components"]["schemas"]
        refresh = document["paths"]["/api/v1/auth/refresh"]["post"]
        assert "requestBody" not in refresh
        assert refresh["responses"]["401"]["x-error-codes"] == ["INVALID_REFRESH_TOKEN"]
        assert document["components"]["responses"]["CsrfRejected"]["x-error-codes"] == [
            "CSRF_TOKEN_MISSING",
            "CSRF_TOKEN_INVALID",
            "ORIGIN_NOT_ALLOWED",
        ]
        assert document["paths"]["/api/v1/auth/csrf"]["get"]["responses"]["200"]["headers"][
            "Cache-Control"
        ] == {"$ref": "#/components/headers/NoStore"}

    assert static_session == generated_session
    assert static["paths"]["/api/v1/auth/refresh"]["post"]["responses"]["409"]["$ref"] == (
        "#/components/responses/RefreshInProgress"
    )
    assert static["components"]["responses"]["RefreshInProgress"]["x-error-codes"] == [
        "REFRESH_IN_PROGRESS"
    ]
    assert generated["paths"]["/api/v1/auth/refresh"]["post"]["responses"]["409"][
        "x-error-codes"
    ] == ["REFRESH_IN_PROGRESS"]
    for path, success_code in (
        ("/api/v1/auth/login", "200"),
        ("/api/v1/auth/signup", "201"),
    ):
        for document in (static, generated):
            responses = document["paths"][path]["post"]["responses"]
            assert {"Set-Cookie", "Cache-Control"} <= set(responses[success_code]["headers"])
            for status_code, response in responses.items():
                assert "Cache-Control" in response["headers"], (path, status_code)
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
