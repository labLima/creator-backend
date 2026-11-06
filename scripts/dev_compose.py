from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def _ensure_local_environment() -> None:
    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    secret_configured = any(
        line.startswith("AUTH_JWT_SECRET=") and line.partition("=")[2].strip() for line in lines
    )
    if secret_configured:
        return

    secret_line = f"AUTH_JWT_SECRET={secrets.token_urlsafe(48)}"
    for index, line in enumerate(lines):
        if line.startswith("AUTH_JWT_SECRET="):
            lines[index] = secret_line
            break
    else:
        lines.append(secret_line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_compose(*arguments: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["docker", "compose", *arguments], cwd=ROOT, env=env, check=True)


PLACEHOLDER_SECRET = "unused-for-local-compose-command"


def _read_env_secret() -> str | None:
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "AUTH_JWT_SECRET":
            return value.strip().strip("\"'") or None
    return None


def _compose_environment(*, command: str) -> dict[str, str]:
    environment = dict(os.environ)
    if command == "start":
        secret = _read_env_secret()
        if secret is None:
            raise SystemExit("AUTH_JWT_SECRET is missing from .env; run make dev/start again")
        # Never let the public placeholder become the start secret, even if
        # it leaked into the caller's shell environment.
        if environment.get("AUTH_JWT_SECRET") in {None, "", PLACEHOLDER_SECRET}:
            environment["AUTH_JWT_SECRET"] = secret
        return environment
    if not environment.get("AUTH_JWT_SECRET"):
        environment["AUTH_JWT_SECRET"] = PLACEHOLDER_SECRET
    return environment


def main(arguments: list[str]) -> int:
    if not arguments or arguments[0] not in {"start", "stop", "clean", "logs"}:
        raise SystemExit("Usage: dev_compose.py {start|stop|clean|logs} [CONFIRM]")

    command = arguments[0]
    if command == "start":
        _ensure_local_environment()
    environment = _compose_environment(command=command)
    if command == "start":
        _run_compose("up", "-d", "--build", "--wait", env=environment)
        _run_compose("ps", env=environment)
    elif command == "stop":
        _run_compose("stop", env=environment)
        print("Serviços parados; containers e volumes preservados.")
    elif command == "clean":
        confirmation = arguments[1] if len(arguments) > 1 else ""
        if confirmation != "yes":
            raise SystemExit("Operação destrutiva. Execute: make dev/clean CONFIRM=yes")
        _run_compose("down", "--volumes", "--remove-orphans", "--rmi", "local", env=environment)
        subprocess.run(["docker", "image", "prune", "-f"], cwd=ROOT, check=True)
        print("Containers, volumes e imagens locais do projeto removidos.")
    else:
        _run_compose("logs", "-f", "--tail=200", env=environment)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
