from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_SECRET = "unused-for-local-compose-command"


def load_dev_compose() -> ModuleType:
    path = ROOT / "scripts" / "dev_compose.py"
    spec = importlib.util.spec_from_file_location("creator_dev_compose_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: ModuleType,
    *,
    env_example_contents: str | None,
) -> tuple[Path, list[dict[str, Any]]]:
    env_file = tmp_path / ".env"
    env_example = tmp_path / ".env.example"
    if env_example_contents is not None:
        env_example.write_text(env_example_contents, encoding="utf-8")
    monkeypatch.setattr(module, "ENV_FILE", env_file)
    monkeypatch.setattr(module, "ENV_EXAMPLE", env_example)
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)

    compose_calls: list[dict[str, Any]] = []

    def fake_run_compose(*arguments: str, env: dict[str, str] | None = None) -> None:
        compose_calls.append({"arguments": arguments, "env": env})

    monkeypatch.setattr(module, "_run_compose", fake_run_compose)
    return env_file, compose_calls


def test_start_does_not_inject_placeholder_jwt_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_dev_compose()
    env_file, compose_calls = prepare_environment(
        monkeypatch,
        tmp_path,
        module,
        env_example_contents="AUTH_JWT_SECRET=local-real-secret\n",
    )

    assert module.main(["start"]) == 0

    assert compose_calls, "start must invoke docker compose"
    for call in compose_calls:
        environment = call["env"] or {}
        injected_secret = environment.get("AUTH_JWT_SECRET")
        assert injected_secret != PLACEHOLDER_SECRET, (
            "start must use the project .env instead of injecting a placeholder AUTH_JWT_SECRET"
        )
        if injected_secret is not None:
            assert injected_secret == "local-real-secret"
    assert "AUTH_JWT_SECRET=local-real-secret" in env_file.read_text(encoding="utf-8")


def test_start_provisions_local_environment_before_building_compose_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_dev_compose()
    env_file, _ = prepare_environment(
        monkeypatch,
        tmp_path,
        module,
        env_example_contents="AUTH_JWT_SECRET=local-real-secret\n",
    )
    env_file.write_text("AUTH_JWT_SECRET=local-real-secret\n", encoding="utf-8")

    order: list[str] = []

    def fake_ensure_local_environment() -> None:
        order.append("ensure-local-environment")

    real_compose_environment = module._compose_environment

    def recording_compose_environment(*args: Any, **kwargs: Any) -> dict[str, str]:
        order.append("build-compose-environment")
        return real_compose_environment(*args, **kwargs)

    monkeypatch.setattr(module, "_ensure_local_environment", fake_ensure_local_environment)
    monkeypatch.setattr(module, "_compose_environment", recording_compose_environment)

    assert module.main(["start"]) == 0

    assert "ensure-local-environment" in order
    assert "build-compose-environment" in order
    assert order.index("ensure-local-environment") < order.index("build-compose-environment"), order


@pytest.mark.parametrize("command", ["stop", "logs"])
def test_non_start_commands_do_not_require_local_environment_provisioning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str
) -> None:
    module = load_dev_compose()
    prepare_environment(
        monkeypatch,
        tmp_path,
        module,
        env_example_contents=None,
    )

    def fail_if_called() -> None:
        raise AssertionError(f"{command} must not provision .env")

    monkeypatch.setattr(module, "_ensure_local_environment", fail_if_called)

    assert module.main([command]) == 0


def test_start_replaces_exported_placeholder_with_env_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_dev_compose()
    env_file = tmp_path / ".env"
    env_file.write_text("AUTH_JWT_SECRET=real-secret\n", encoding="utf-8")
    monkeypatch.setattr(module, "ENV_FILE", env_file)
    monkeypatch.setenv("AUTH_JWT_SECRET", module.PLACEHOLDER_SECRET)

    environment = module._compose_environment(command="start")

    assert environment["AUTH_JWT_SECRET"] == "real-secret"
