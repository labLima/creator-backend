"""Enforce the import direction that keeps capabilities independent.

Layout: `src/creator/<capability>/` with a fixed file vocabulary. The rules
below are the only thing preventing `billing/router.py` from importing
`plan/service.py` and re-coupling the codebase the refactor just separated.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREATOR_ROOT = PROJECT_ROOT / "src" / "creator"


# A capability is any directory that exposes HTTP routes.
def _capabilities() -> list[Path]:
    return sorted(
        path
        for path in CREATOR_ROOT.iterdir()
        if path.is_dir()
        and path.name not in {"__pycache__", "api"}
        and (path / "router.py").exists()
    )


# Files that must never touch persistence or transport internals.
PURE_KINDS = {
    "schemas.py",
    "service.py",
    "ports.py",
    "policy.py",
    "exceptions.py",
    "generation_service.py",
    "improvement_service.py",
    "storage_service.py",
}

# Files allowed to import SQLAlchemy and `creator.infrastructure`.
SQL_KINDS = {"models.py", "repository.py"}

# Cross-capability imports are only legal for these file kinds.
SHARED_KINDS = {"schemas.py", "ports.py", "exceptions.py", "models.py"}

FORBIDDEN_THIRD_PARTY = {"sqlalchemy", "fastapi", "starlette", "jwt"}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for capability in _capabilities():
        files.extend(path for path in capability.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def _resolved_imports(path: Path) -> list[tuple[int, str, tuple[str, ...]]]:
    """Return `(lineno, absolute_module, imported_names)`.

    `ast.ImportFrom.module` drops the leading dots, so a relative import would
    otherwise bypass every rule. Re-anchor against `src/creator`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = list(path.parent.relative_to(CREATOR_ROOT).parts)
    resolved: list[tuple[int, str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            resolved.extend((node.lineno, alias.name, ()) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = ["creator", *package]
                base = base[: len(base) - (node.level - 1)]
                module = ".".join([*base, node.module]) if node.module else ".".join(base)
            else:
                module = node.module or ""
            resolved.append((node.lineno, module, tuple(alias.name for alias in node.names)))
    return resolved


def _capability_of(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != "creator":
        return None
    if parts[1] == "api":
        return None
    candidate = CREATOR_ROOT / parts[1]
    if candidate.is_dir() and (candidate / "router.py").exists():
        return parts[1]
    return None


def test_capability_set_is_exact() -> None:
    names = {path.name for path in _capabilities()}

    assert len(names) == 27, sorted(names)
    assert {"auth", "user", "workspace", "brand", "generation", "billing_provider"} <= names


REQUIRED_CAPABILITY_FILES = (
    "__init__.py",
    "router.py",
    "service.py",
    "repository.py",
    "models.py",
    "schemas.py",
    "ports.py",
)


def test_capabilities_expose_the_full_file_vocabulary() -> None:
    """Every capability must expose the same structural vocabulary.

    A missing file is usually a DTO or use case parked in the wrong package,
    which is how `ImageWorkflowRequest` ended up in `generation/schemas.py`.
    """
    missing: dict[str, list[str]] = {}
    for capability in _capabilities():
        absent = [name for name in REQUIRED_CAPABILITY_FILES if not (capability / name).exists()]
        if absent:
            missing[capability.name] = absent

    assert not missing, f"capabilities missing required files: {missing}"


def test_legacy_package_layouts_are_gone() -> None:
    """The pre-refactor catch-all packages must not come back."""
    legacy = (
        CREATOR_ROOT / "modules",
        CREATOR_ROOT / "repositories",
        CREATOR_ROOT / "infrastructure" / "persistence" / "repositories",
    )
    surviving = [path.relative_to(PROJECT_ROOT).as_posix() for path in legacy if path.exists()]
    surviving.extend(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in CREATOR_ROOT.glob("*/adapters")
        if path.exists()
    )

    assert not surviving, f"legacy package layout reintroduced: {surviving}"


HTTP_RESPONSE_NAMES = frozenset(
    {
        "success_response",
        "error_response",
        "JSONResponse",
        "Response",
        "PlainTextResponse",
        "StreamingResponse",
        "FileResponse",
        "RedirectResponse",
        "HTMLResponse",
        "ORJSONResponse",
    }
)
HTTP_RESPONSE_MODULES = frozenset(
    {
        "api.responses",
        "creator.api.responses",
        "fastapi",
        "fastapi.responses",
        "starlette",
        "starlette.responses",
    }
)


def _response_aliases(tree: ast.AST) -> dict[str, str]:
    """Map local aliases to the canonical HTTP response name."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module not in HTTP_RESPONSE_MODULES:
            continue
        for alias in node.names:
            if alias.name in HTTP_RESPONSE_NAMES:
                aliases[alias.asname or alias.name] = alias.name
    return aliases


def _service_response_violations(source: str, path: str) -> list[str]:
    tree = ast.parse(source)
    aliases = _response_aliases(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in HTTP_RESPONSE_MODULES:
            for alias in node.names:
                if alias.name in HTTP_RESPONSE_NAMES:
                    violations.append(f"{path}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name is None:
                continue
            canonical = aliases.get(name, name)
            if canonical in HTTP_RESPONSE_NAMES:
                violations.append(f"{path}:{node.lineno} calls {canonical}()")
    return violations


def test_services_never_build_http_responses() -> None:
    """Services return payloads; only routers own the response envelope.

    `asset/service.py` returned `success_response(...)`, which the router wrapped
    again, turning every brand asset read into a 500 serialisation error. The
    detector also rejects aliases, relative imports and direct response classes.
    """
    violations: list[str] = []
    scanned = 0
    for service in _python_files():
        if not service.name.endswith("service.py"):
            continue
        scanned += 1
        violations.extend(
            _service_response_violations(
                service.read_text(encoding="utf-8"),
                service.relative_to(PROJECT_ROOT).as_posix(),
            )
        )

    assert scanned >= len(_capabilities()), (
        f"service response scan only inspected {scanned} files (vacuous?)"
    )
    assert not violations, "\n".join(violations)


def test_service_response_guard_detects_aliases_and_response_classes() -> None:
    source = """
from creator.api.responses import success_response as ok
from fastapi.responses import JSONResponse as Json
from ..api.responses import error_response as bad
from fastapi import Response as Raw

def handler():
    ok({})
    bad({})
    Raw({})
    return Json({})
"""
    violations = _service_response_violations(source, "sample.py")

    assert len(violations) == 8, violations
    assert sum("success_response" in item for item in violations) == 2
    assert sum("error_response" in item for item in violations) == 2
    assert sum("JSONResponse" in item for item in violations) == 2
    assert sum("calls Response()" in item for item in violations) == 1


def test_relative_imports_are_anchored_on_creator(tmp_path, monkeypatch) -> None:
    root = tmp_path / "src" / "creator"
    (root / "asset").mkdir(parents=True)
    service = root / "asset" / "service.py"
    service.write_text(
        "from .models import Asset\nfrom ..api.responses import success_response\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "CREATOR_ROOT", root)

    imports = _resolved_imports(service)

    assert [module for _, module, _ in imports] == [
        "creator.asset.models",
        "creator.api.responses",
    ]


def test_pure_files_do_not_import_persistence_or_transport() -> None:
    scanned = 0
    for path in _python_files():
        if path.name not in PURE_KINDS:
            continue
        scanned += 1
        for lineno, module, _ in _resolved_imports(path):
            root = module.split(".")[0]
            assert root not in FORBIDDEN_THIRD_PARTY, (
                f"{path.relative_to(PROJECT_ROOT)}:{lineno} imports {module}"
            )
            assert not module.startswith("creator.infrastructure"), (
                f"{path.relative_to(PROJECT_ROOT)}:{lineno} imports infrastructure"
            )

    assert scanned >= 30, f"boundary scan only inspected {scanned} files (vacuous?)"


def test_only_models_and_repository_touch_infrastructure() -> None:
    violations: list[str] = []
    for path in _python_files():
        if path.name in SQL_KINDS:
            continue
        for lineno, module, _ in _resolved_imports(path):
            if module.startswith("creator.infrastructure"):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno} -> {module}")

    assert not violations, "\n".join(violations)


def test_cross_capability_imports_use_shared_kinds_only() -> None:
    violations: list[str] = []
    for path in _python_files():
        if path.name == "__init__.py":
            continue
        source = path.parent.name
        for lineno, module, names in _resolved_imports(path):
            target = _capability_of(module)
            candidates = [module]
            for name in names:
                nested = f"{module}.{name}"
                if _capability_of(nested) is not None:
                    candidates.append(nested)
                    target = target or _capability_of(nested)
            if target is None or target == source:
                continue
            # Any file may consume another capability's shared vocabulary
            # (`ports`, `schemas`, `exceptions`, `models`); behaviour is never
            # shared. A bare package import is allowed when one of the imported
            # names is a shared kind (e.g. `from creator.workspace import models`).
            kinds = {
                f"{candidate.split('.')[2]}.py"
                if len(candidate.split(".")) > 2 and candidate.split(".")[1] == target
                else "__init__"
                for candidate in candidates
            }
            if kinds & SHARED_KINDS:
                continue
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)}:{lineno} -> {module} "
                f"({path.name} may not import {sorted(kinds)} of {target})"
            )

    assert not violations, "\n".join(violations)


def test_capabilities_never_import_the_application_entrypoint() -> None:
    violations = [
        f"{path.relative_to(PROJECT_ROOT)}:{lineno}"
        for path in _python_files()
        for lineno, module, names in _resolved_imports(path)
        if module in {"creator.main", "creator.api.router"}
        or (module == "creator" and {"main", "api"} & set(names))
    ]

    assert not violations, "\n".join(violations)


def _assert_acyclic(graph: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: tuple[str, ...]) -> None:
        if node in visiting:
            raise AssertionError("import cycle: " + " -> ".join((*trail, node)))
        if node in visited:
            return
        visiting.add(node)
        for neighbour in sorted(graph.get(node, ())):
            visit(neighbour, (*trail, node))
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node, ())


def test_capability_import_graph_is_acyclic() -> None:
    """Behavioural edges must be acyclic.

    `models.py` edges are excluded: declarative tables form one metadata graph
    and a mutual reference there is invisible to Python (foreign keys are
    strings), whereas a repository -> repository edge is a real cycle.
    """
    graph: dict[str, set[str]] = {}
    for path in _python_files():
        source = path.parent.name
        graph.setdefault(source, set())
        for _, module, names in _resolved_imports(path):
            targets: set[str] = set()
            target = _capability_of(module)
            if target:
                targets.add(target)
            for name in names:
                nested = _capability_of(f"{module}.{name}")
                if nested:
                    targets.add(nested)
            if path.name == "models.py":
                continue
            for candidate in targets:
                if candidate == source:
                    continue
                # A models-only edge is not a behavioural dependency.
                if module == f"creator.{candidate}" and "models" in names:
                    continue
                if module == f"creator.{candidate}.models":
                    continue
                graph[source].add(candidate)

    _assert_acyclic(graph)
