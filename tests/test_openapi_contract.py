from __future__ import annotations

from pathlib import Path

import yaml

from creator.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/auth/refresh",
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


def test_static_openapi_declares_creator_bearer_security() -> None:
    static = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))

    assert static["components"]["securitySchemes"]["CreatorBearerAuth"]["scheme"] == "bearer"
    for path, item in static["paths"].items():
        if not path.startswith("/api/v1/") or path in PUBLIC_AUTH_PATHS:
            continue
        for method in _operations(item):
            assert item[method].get("security") == [{"CreatorBearerAuth": []}], (method, path)


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
