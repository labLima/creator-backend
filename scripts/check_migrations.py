"""Run the migration drift check against an isolated SQLite database."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    database_path = Path(".local/db/alembic-check.db").resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path.as_posix()}"

    try:
        for command in (
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            [sys.executable, "-m", "alembic", "check"],
        ):
            subprocess.run(command, check=True, env=environment)
    except subprocess.CalledProcessError as error:
        return error.returncode
    finally:
        database_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
