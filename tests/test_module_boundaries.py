"""Enforce the import direction that keeps capabilities independent.

The refactor is only durable if the boundary is machine-checked. Today the
rules below are true by construction; without this test the next shortcut
(`from creator.modules.billing.service import ...`) re-couples everything.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = PROJECT_ROOT / "src" / "creator" / "modules"

# Files that may never touch persistence or transport infrastructure.
PURE_KINDS = {
    "schemas.py",
    "service.py",
    "ports.py",
    "types.py",
    "generation_service.py",
    "improvement_service.py",
    "storage_service.py",
    "exceptions.py",
    "policy.py",
}

# Cross-capability imports are only legal for these file kinds.
SHARED_KINDS = {"schemas.py", "ports.py", "types.py", "exceptions.py"}

FORBIDDEN_THIRD_PARTY = {"sqlalchemy", "fastapi", "starlette"}

PACKAGE_ROOTS = {"creator"}


def _python_files() -> list[Path]:
    return sorted(path for path in MODULES_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
    return found


def test_modules_directory_matches_expected_capabilities() -> None:
    discovered = {
        path.name for path in MODULES_ROOT.iterdir() if path.is_dir() and path.name != "__pycache__"
    }

    assert len(discovered) == 27, sorted(discovered)
    assert {"auth", "user", "workspace", "brand", "generation", "billing_provider"} <= discovered


def test_pure_files_do_not_import_persistence_or_transport() -> None:
    scanned = 0
    for path in _python_files():
        if path.name not in PURE_KINDS:
            continue
        scanned += 1
        for lineno, module in _imports(path):
            root = module.split(".")[0]
            assert root not in FORBIDDEN_THIRD_PARTY, (
                f"{path.relative_to(PROJECT_ROOT)}:{lineno} imports {module}"
            )
            if module.startswith("creator.infrastructure"):
                raise AssertionError(
                    f"{path.relative_to(PROJECT_ROOT)}:{lineno} imports infrastructure"
                )

    assert scanned >= 30, f"boundary scan only inspected {scanned} files (vacuous?)"


def test_cross_capability_imports_use_shared_kinds_only() -> None:
    violations: list[str] = []
    for path in _python_files():
        if path.name == "__init__.py":
            continue
        source_module = path.parent.name
        for lineno, module in _imports(path):
            parts = module.split(".")
            if len(parts) < 3 or parts[:2] != ["creator", "modules"]:
                continue
            target_module = parts[2]
            if target_module == source_module:
                continue
            target_kind = parts[3] if len(parts) > 3 else "__init__"
            if path.name in SHARED_KINDS and f"{target_kind}.py" in SHARED_KINDS:
                continue
            if path.name not in SHARED_KINDS and f"{target_kind}.py" in SHARED_KINDS:
                continue
            violations.append(
                f"{path.relative_to(PROJECT_ROOT)}:{lineno} -> {module} "
                f"({path.name} may not import {target_kind}.py of {target_module})"
            )

    assert not violations, "\n".join(violations)


def test_modules_never_import_the_application_entrypoint() -> None:
    violations = [
        f"{path.relative_to(PROJECT_ROOT)}:{lineno}"
        for path in _python_files()
        for lineno, module in _imports(path)
        if module in {"creator.main", "creator.api.router"}
    ]

    assert not violations, "\n".join(violations)


def test_capability_import_graph_is_acyclic() -> None:
    graph: dict[str, set[str]] = {}
    for path in _python_files():
        source = path.parent.name
        graph.setdefault(source, set())
        for _, module in _imports(path):
            parts = module.split(".")
            if len(parts) >= 3 and parts[:2] == ["creator", "modules"] and parts[2] != source:
                graph[source].add(parts[2])

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
