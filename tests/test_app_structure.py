import ast
import importlib
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_executable_app_modules_are_importable() -> None:
    module_names = [
        "creator.api",
        "creator.api.router",
        "creator.api.errors",
        "creator.api.serializers",
        "creator.api.openapi",
        "creator.core.pagination",
        "creator.config",
        "creator.domain",
        "creator.infrastructure",
        "creator.infrastructure.auth",
        "creator.infrastructure.database",
        "creator.infrastructure.database.metadata",
        "creator.infrastructure.persistence",
        "creator.infrastructure.runtime",
        "creator.integrations",
        "creator.services",
        "creator.uow",
    ]
    module_names.extend(
        f"creator.{path.name}"
        for path in sorted((PROJECT_ROOT / "src/creator").iterdir())
        if path.is_dir()
        and path.name not in {"__pycache__", "api"}
        and (path / "router.py").exists()
    )
    for module_name in module_names:
        assert importlib.import_module(module_name)


def test_container_image_includes_alembic_artifacts() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY alembic.ini ./" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile


def test_infrastructure_is_split_by_adapter_boundary() -> None:
    infrastructure = PROJECT_ROOT / "src" / "creator" / "infrastructure"

    assert {path.name for path in infrastructure.iterdir() if path.is_file()} == {"__init__.py"}
    assert {
        path.name
        for path in infrastructure.iterdir()
        if path.is_dir() and path.name != "__pycache__" and any(path.rglob("*.py"))
    } == {"auth", "database", "persistence", "runtime"}


def test_application_and_domain_do_not_import_transport_or_infrastructure() -> None:
    forbidden_modules = {
        "fastapi",
        "fastapi_jwt_auth",
        "jwt",
        "starlette",
    }
    scanned = 0
    roots = [
        PROJECT_ROOT / "src" / "creator" / "domain",
        PROJECT_ROOT / "src" / "creator" / "core",
    ]
    roots.extend(
        path
        for path in (PROJECT_ROOT / "src/creator").iterdir()
        if path.is_dir()
        and path.name not in {"__pycache__", "api"}
        and (path / "router.py").exists()
    )
    for root in roots:
        for path in root.rglob("*.py"):
            if path.name in {"router.py", "models.py", "repository.py"}:
                continue
            scanned += 1
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = [alias.name.split(".")[0] for alias in node.names]
                    assert not set(imported) & forbidden_modules, path
                elif isinstance(node, ast.ImportFrom):
                    module = (node.module or "").split(".")
                    assert not set(module[:1]) & forbidden_modules, path
                    assert module[:2] != ["creator", "infrastructure"], path
                    imported_names = {alias.name for alias in node.names}
                    assert not imported_names & {"Request", "Response"}, path

    assert scanned >= 30, f"boundary scan only inspected {scanned} files (vacuous?)"


def test_compose_runs_migrations_before_api_and_worker() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  migrate:" in compose
    assert 'command: ["alembic", "upgrade", "head"]' in compose
    assert 'command: ["creator-worker", "all"]' in compose
    assert compose.count("condition: service_completed_successfully") == 2


def test_business_routes_require_authenticated_principal() -> None:
    """Every `/api/v1` route except the public auth trio resolves a Principal.

    Runtime introspection instead of a source scan: routers use prefixes and are
    nested (FastAPI 0.162 keeps them inside `_IncludedRouter`), so an AST scan
    misses `/api/v1/auth/*` and can silently pass on zero handlers.
    """
    from fastapi.routing import APIRoute

    from creator.main import app

    app.openapi()  # force lazy router expansion so nested routes are materialised

    def walk(router: object) -> list[APIRoute]:
        found: list[APIRoute] = []
        for route in getattr(router, "routes", []):
            if isinstance(route, APIRoute):
                found.append(route)
                continue
            nested = getattr(route, "original_router", None)
            if nested is not None:
                found.extend(walk(nested))
        return found

    def dependency_names(route: APIRoute) -> set[str]:
        names: set[str] = set()
        stack = [route.dependant]
        while stack:
            dependant = stack.pop()
            if dependant.call is not None:
                names.add(getattr(dependant.call, "__name__", str(dependant.call)))
            stack.extend(dependant.dependencies)
        return names

    principal_resolvers = {
        "get_principal",
        "get_optional_principal",
        "get_current_user",
        "get_optional_current_user",
    }
    public = {"/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/refresh"}

    routes = [route for route in walk(app) if route.path_format.startswith("/api/v1/")]
    unauthenticated = [
        route.path_format
        for route in routes
        if route.path_format not in public and not dependency_names(route) & principal_resolvers
    ]

    assert len(routes) == 224, f"expected 224 /api/v1 operations, found {len(routes)}"
    assert not unauthenticated, f"routes without a Principal dependency: {unauthenticated}"


def test_openapi_declares_cookie_security_for_business_operations() -> None:
    document = yaml.safe_load((PROJECT_ROOT / "docs/openapi.yaml").read_text(encoding="utf-8"))
    public_routes = {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
    }

    for path, operations in document["paths"].items():
        if not path.startswith("/api/v1/") or path in public_routes:
            continue
        for method, operation in operations.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                if path in {"/api/v1/auth/refresh", "/api/v1/auth/csrf"}:
                    expected_security = []
                else:
                    expected_security = [{"CreatorSessionCookie": []}]
                assert operation.get("security") == expected_security, (
                    f"{method.upper()} {path} must declare cookie security"
                )
