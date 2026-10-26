from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from creator.api.dependencies import get_llm_provider, get_settings, get_uow
from creator.config import Settings
from creator.infrastructure.db import create_database_engine
from creator.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from creator.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRET = "test-e2e-local-auth-secret-with-32-bytes"


class FakeLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        self.prompts.append(prompt)
        return "Generated launch copy"


@pytest.fixture()
def e2e(tmp_path: Path) -> Generator[tuple[object, FakeLLM], None, None]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'e2e.db'}"
    engine: Engine = create_database_engine(database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        auth_jwt_secret=SECRET,
        auth_password_min_length=8,
        auth_access_token_ttl_seconds=900,
        auth_refresh_token_ttl_days=1,
        rate_limit_backend="memory",
        storage_provider="local",
        local_storage_root=str(tmp_path / "storage"),
    )
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_llm_provider] = FakeLLM

    def uow_override() -> Generator[SqlAlchemyUnitOfWork, None, None]:
        with SqlAlchemyUnitOfWork(factory) as unit_of_work:
            yield unit_of_work

    application.dependency_overrides[get_uow] = uow_override
    llm = FakeLLM()
    application.dependency_overrides[get_llm_provider] = lambda: llm
    try:
        yield application, llm
    finally:
        engine.dispose()


def signup_payload(email: str, workspace: str = "Creator Workspace") -> dict[str, object]:
    return {
        "email": email,
        "password": "correct-password",
        "workspace": {"name": workspace},
    }
