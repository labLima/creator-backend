import ast
import importlib
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_executable_app_modules_are_importable() -> None:
    for module_name in [
        "creator.api",
        "creator.config",
        "creator.domain",
        "creator.infrastructure",
        "creator.infrastructure.auth",
        "creator.infrastructure.database",
        "creator.infrastructure.database.models",
        "creator.infrastructure.persistence",
        "creator.infrastructure.persistence.repositories",
        "creator.infrastructure.runtime",
        "creator.integrations",
        "creator.repositories",
        "creator.services",
    ]:
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
    for layer in ("application", "domain"):
        root = PROJECT_ROOT / "src" / "creator" / layer
        for path in root.rglob("*.py"):
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


def test_compose_runs_migrations_before_api_and_worker() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  migrate:" in compose
    assert 'command: ["alembic", "upgrade", "head"]' in compose
    assert 'command: ["creator-worker", "all"]' in compose
    assert compose.count("condition: service_completed_successfully") == 2


def test_business_routes_require_authenticated_principal() -> None:
    tree = ast.parse((PROJECT_ROOT / "src/creator/main.py").read_text(encoding="utf-8"))
    public_routes = {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/refresh",
    }

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        route_paths = {
            decorator.args[0].value
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in {"get", "post", "put", "patch", "delete"}
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and isinstance(decorator.args[0].value, str)
            and decorator.args[0].value.startswith("/api/v1/")
        }
        if not route_paths or route_paths & public_routes:
            continue
        argument_names = {argument.arg for argument in node.args.args + node.args.kwonlyargs}
        assert "current_user" in argument_names, (
            f"Protected route handler {node.name} must depend on current_user"
        )


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
                if path == "/api/v1/auth/refresh":
                    expected_security = [{"CreatorRefreshCookie": []}]
                elif path == "/api/v1/auth/csrf":
                    expected_security = [
                        {"CreatorSessionCookie": []},
                        {"CreatorRefreshCookie": []},
                        {"CreatorLegacyBearerAuth": []},
                    ]
                else:
                    expected_security = [{"CreatorSessionCookie": []}]
                    expected_security.append({"CreatorLegacyBearerAuth": []})
                assert operation.get("security") == expected_security, (
                    f"{method.upper()} {path} must declare cookie security"
                )
