"""Keep the coverage gate honest while packages are being deleted.

`pyproject.toml` lists `--cov=creator.application`, `--cov=creator.services`
and `--cov=creator.repositories`. The refactor deletes all three. Without this
test, pytest-cov would keep measuring only the surviving packages and
`--cov-fail-under=80` would pass with almost no real coverage.
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
