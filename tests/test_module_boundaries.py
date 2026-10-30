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


def _resolved_imports(path: Path) -> list[tuple[int, str, tuple[str, ...]]]:
    """Return `(lineno, absolute_module, imported_names)` for every import.

    `ast.ImportFrom.module` drops the leading dots, so `from ..billing.service
    import X` inside `modules/generation/router.py` is recorded as
    `billing.service`. Every rule above then skips it because `len(parts) < 3`
    and the entrypoint rule misses it because it is not literally
    `creator.main`. Re-anchoring the level against the file's own package
    closes that hole: a single relative import otherwise bypasses the
    cross-capability rule, the acyclicity rule and the entrypoint rule at once.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = list(path.parent.relative_to(MODULES_ROOT.parent.parent).parts)
    resolved: list[tuple[int, str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            resolved.extend((node.lineno, alias.name, ()) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = package[: len(package) - (node.level - 1)] if node.level else []
            module = ".".join([*base, node.module]) if node.module else ".".join(base)
            resolved.append((node.lineno, module, tuple(alias.name for alias in node.names)))
    return resolved


def test_relative_and_aliased_imports_respect_capability_boundaries() -> None:
    violations: list[str] = []
    graph: dict[str, set[str]] = {}
    for path in _python_files():
        source = path.parent.name
        graph.setdefault(source, set())
        for lineno, module, names in _resolved_imports(path):
            where = f"{path.relative_to(PROJECT_ROOT)}:{lineno}"
            parts = module.split(".")
            # A package import (`from creator.modules.billing import service`)
            # names a submodule; the bare package is not itself a violation.
            candidates = [module] if len(parts) >= 4 else []
            if len(parts) == 3 and parts[:2] == ["creator", "modules"]:
                candidates = [f"{module}.{name}" for name in names]
            for candidate in [module, *candidates]:
                candidate_root = candidate.split(".")[0]
                if path.name in PURE_KINDS and candidate_root in FORBIDDEN_THIRD_PARTY:
                    violations.append(f"{where} imports {candidate}")
                if "adapters" not in path.parts and candidate.startswith("creator.infrastructure"):
                    violations.append(f"{where} imports infrastructure ({candidate})")
            for candidate in [module, *(f"{module}.{name}" for name in names)]:
                if candidate in {"creator.main", "creator.api.router"}:
                    violations.append(f"{where} imports the application entrypoint ({candidate})")
            if len(parts) < 3 or parts[:2] != ["creator", "modules"]:
                continue
            target = parts[2]
            if target == source:
                continue
            graph[source].add(target)
            for candidate in candidates:
                kind_parts = candidate.split(".")
                kind = kind_parts[3] if len(kind_parts) > 3 else "__init__"
                if path.name == "__init__.py" and kind == "__init__":
                    # A package's own `__init__` is its public surface; only
                    # explicitly named submodules are subject to the kind rule.
                    continue
                if f"{kind}.py" not in SHARED_KINDS:
                    violations.append(
                        f"{where} -> {candidate} ({path.name} may not import {kind}.py of {target})"
                    )

    assert not violations, "\n".join(violations)

    _assert_acyclic(graph)


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
    graph: dict[str, set[str]] = {}
    for path in _python_files():
        source = path.parent.name
        graph.setdefault(source, set())
        for _, module in _imports(path):
            parts = module.split(".")
            if len(parts) >= 3 and parts[:2] == ["creator", "modules"] and parts[2] != source:
                graph[source].add(parts[2])

    _assert_acyclic(graph)
