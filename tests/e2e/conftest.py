from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from creator.api.dependencies import (
    get_generation_queue,
    get_llm_provider,
    get_settings,
    get_storage_provider,
    get_uow,
)
from creator.config import Settings
from creator.infrastructure.db import create_database_engine
from creator.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from creator.main import create_app
from creator.services.ai.image_provider import ImageGenerationRequest, ImageGenerationResult
from creator.services.storage.provider import (
    StoredObject,
    StoredObjectMetadata,
    UploadObjectRequest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRET = "test-e2e-local-auth-secret-with-32-bytes"


class FakeLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.improvement_response = json.dumps(
            {
                "text": "Improved launch copy",
                "justification": "The copy is clearer and more direct.",
            }
        )

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        self.prompts.append(prompt)
        if "improvement." in prompt:
            return self.improvement_response
        return "Generated launch copy"


class FakeGenerationQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, UUID]] = []
        self.error: Exception | None = None

    def enqueue_image_generation(self, *, job_id: UUID, request_id: UUID) -> object:
        if self.error is not None:
            raise self.error
        self.calls.append({"job_id": job_id, "request_id": request_id})
        return object()


class FakeImageGenerator:
    def __init__(self) -> None:
        self.requests: list[ImageGenerationRequest] = []

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        self.requests.append(request)
        return ImageGenerationResult(
            image_bytes=b"fake-image-bytes",
            mime_type="image/png",
            width=640,
            height=480,
            model=request.model or "fake-image-model",
            prompt=request.prompt,
            metadata={"provider": "fake-image"},
        )


class FakeStorageProvider:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.uploads: list[UploadObjectRequest] = []

    def upload(self, request: UploadObjectRequest) -> StoredObject:
        self.objects[request.path] = request.content
        self.uploads.append(request)
        return StoredObject(
            path=request.path,
            url=f"https://storage.test/{request.path}",
            mime_type=request.mime_type,
            size_bytes=len(request.content),
            checksum_sha256=request.checksum_sha256 or "fake-checksum",
            metadata={"provider": "fake-storage", **request.metadata},
        )

    def delete(self, path: str) -> None:
        self.objects.pop(path, None)

    def get_url(self, path: str) -> str:
        return f"https://storage.test/{path}"

    def stat(self, path: str) -> StoredObjectMetadata:
        content = self.objects[path]
        return StoredObjectMetadata(
            path=path,
            mime_type="image/png",
            size_bytes=len(content),
            checksum_sha256="fake-checksum",
            metadata={"provider": "fake-storage"},
        )

    def download(self, path: str, *, max_bytes: int) -> bytes:
        content = self.objects[path]
        if len(content) > max_bytes:
            raise ValueError("fake object exceeds max size")
        return content


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
        rate_limit_limit=100,
        storage_provider="local",
        local_storage_root=str(tmp_path / "storage"),
    )
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings

    def uow_override() -> Generator[SqlAlchemyUnitOfWork, None, None]:
        with SqlAlchemyUnitOfWork(factory) as unit_of_work:
            yield unit_of_work

    application.dependency_overrides[get_uow] = uow_override
    llm = FakeLLM()
    queue = FakeGenerationQueue()
    image_generator = FakeImageGenerator()
    storage = FakeStorageProvider()
    application.dependency_overrides[get_llm_provider] = lambda: llm
    application.dependency_overrides[get_generation_queue] = lambda: queue
    application.dependency_overrides[get_storage_provider] = lambda: storage
    application.state.e2e_settings = settings
    application.state.e2e_factory = factory
    application.state.e2e_queue = queue
    application.state.e2e_image_generator = image_generator
    application.state.e2e_storage = storage
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
