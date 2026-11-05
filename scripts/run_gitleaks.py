"""Run the repository's Gitleaks configuration with a local CLI or Docker image."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    executable = shutil.which("gitleaks")
    if executable is not None:
        command = [
            executable,
            "detect",
            "--source",
            str(PROJECT_ROOT),
            "--no-banner",
            "--redact",
            "--config",
            str(PROJECT_ROOT / ".gitleaks.toml"),
        ]
    else:
        docker = shutil.which("docker")
        if docker is None:
            raise SystemExit("Gitleaks is unavailable: install gitleaks or Docker")
        command = [
            docker,
            "run",
            "--rm",
            "-v",
            f"{PROJECT_ROOT.resolve()}:/repo",
            "zricethezav/gitleaks:latest",
            "detect",
            "--source",
            "/repo",
            "--no-git",
            "--no-banner",
            "--redact",
            "--config",
            "/repo/.gitleaks.toml",
        ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
