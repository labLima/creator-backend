"""Enforce the import direction that keeps capabilities independent.

Layout: `src/creator/<capability>/` with a fixed file vocabulary. The rules
below are the only thing preventing `billing/router.py` from importing
`plan/service.py` and re-coupling the codebase the refactor just separated.
"""

from __future__ import annotations

import ast
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
            base = package[: len(package) - (node.level - 1)] if node.level else []
            module = ".".join([*base, node.module]) if node.module else ".".join(base)
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
            if target is None:
                for name in names:
                    nested = f"{module}.{name}"
                    if _capability_of(nested) is not None:
                        candidates.append(nested)
                        target = target or _capability_of(nested)
            if target is None or target == source:
                continue
            for candidate in candidates:
                parts = candidate.split(".")
                kind = f"{parts[2]}.py" if len(parts) > 2 and parts[1] == target else "__init__"
                # Any file may consume another capability's shared vocabulary
                # (`ports`, `schemas`, `exceptions`, `models`); behaviour is
                # never shared.
                if kind in SHARED_KINDS:
                    continue
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{lineno} -> {candidate} "
                    f"({path.name} may not import {kind} of {target})"
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
    graph: dict[str, set[str]] = {}
    for path in _python_files():
        source = path.parent.name
        graph.setdefault(source, set())
        for _, module, names in _resolved_imports(path):
            target = _capability_of(module)
            if target is None:
                for name in names:
                    target = _capability_of(f"{module}.{name}")
                    if target:
                        break
            if target and target != source:
                graph[source].add(target)

    _assert_acyclic(graph)
