"""Keep the coverage gate honest.

The gate measures the whole `creator` package (8.8k statements) minus HTTP
routers, which are covered by the e2e suite. The floor is 75%: the previous
configuration measured a 3.4k-statement subset at 80%, so this is a larger
surface with a lower percentage, not a relaxed gate.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _coverage_targets() -> list[str]:
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    if isinstance(addopts, str):
        addopts = addopts.split()
    return [arg.removeprefix("--cov=") for arg in addopts if arg.startswith("--cov=")]


def test_coverage_targets_are_declared() -> None:
    assert _coverage_targets()


def test_every_coverage_target_is_importable() -> None:
    for target in _coverage_targets():
        assert importlib.util.find_spec(target) is not None, (
            f"coverage target {target!r} no longer resolves; update pyproject.toml "
            "in the same change that deletes the package"
        )


def test_coverage_floor_is_configured() -> None:
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    if isinstance(addopts, list):
        addopts = " ".join(addopts)

    assert re.search(r"--cov-fail-under=\d+", addopts)
