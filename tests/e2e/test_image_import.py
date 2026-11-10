from __future__ import annotations

from io import BytesIO
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from PIL import Image

from creator.asset.repository import SqlAlchemyAssetRepository
from creator.content.models import Image as ImageRow
from creator.content.repository import SqlAlchemyContentRepository
from creator.services.agents.contracts import AgentExecutionResult, ArtistOutput
from creator.services.ai.image_provider import ImageGenerationRequest, ImageGenerationResult
from creator.services.storage.provider import StorageUploadError
from creator.workers import image_generation as worker
from tests.e2e.conftest import PROJECT_ROOT
from tests.e2e.test_content_flow import _signup
from tests.e2e.test_contract_flows import _patch_worker_to_test_database

pytestmark = pytest.mark.e2e


@pytest.mark.anyio
async def test_reference_image_upload_checks_brand_format_and_size(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        owner, workspace = await _signup(client, "reference-owner@example.com")
        outsider, _ = await _signup(client, "reference-outsider@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=owner,
            json={"workspace_id": workspace, "name": "Reference Brand"},
        )
        assert brand_response.status_code == 201, brand_response.text
        brand_id = brand_response.json()["data"]["id"]
        data = BytesIO()
        Image.new("RGB", (16, 12), "blue").save(data, format="PNG")
        uploaded = await client.post(
            "/api/v1/assets/reference-images",
            headers=owner,
            data={"workspace_id": workspace, "brand_id": brand_id},
            files={"file": ("reference.png", data.getvalue(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        asset = uploaded.json()["data"]
        assert asset["asset_type"] == "REFERENCE_IMAGE"
        assert asset["workspace_id"] == workspace and asset["brand_id"] == brand_id
        assert asset["byte_size"] == len(data.getvalue())
        assert asset["checksum"]
        invalid = await client.post(
            "/api/v1/assets/reference-images",
            headers=owner,
            data={"workspace_id": workspace, "brand_id": brand_id},
            files={"file": ("reference.png", b"not an image", "image/png")},
        )
        assert invalid.status_code == 422
        oversized = await client.post(
            "/api/v1/assets/reference-images",
            headers=owner,
            data={"workspace_id": workspace, "brand_id": brand_id},
            files={
                "file": (
                    "large.png",
                    b"x" * (10 * 1024 * 1024 + 1),
                    "image/png",
                )
            },
        )
        assert oversized.status_code == 413
        denied = await client.post(
            "/api/v1/assets/reference-images",
            headers=outsider,
            data={"workspace_id": workspace, "brand_id": brand_id},
            files={"file": ("reference.png", data.getvalue(), "image/png")},
        )
        assert denied.status_code == 404


@pytest.mark.anyio
async def test_reference_upload_deletes_object_when_asset_persistence_fails(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    storage = application.state.e2e_storage
    data = BytesIO()
    Image.new("RGB", (12, 12), "green").save(data, format="PNG")
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        owner, workspace = await _signup(client, "reference-cleanup@example.com")
        brand = (
            await client.post(
                "/api/v1/brands",
                headers=owner,
                json={"workspace_id": workspace, "name": "Reference Brand"},
            )
        ).json()["data"]["id"]

        def fail(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("database failure")

        monkeypatch.setattr(SqlAlchemyAssetRepository, "add", fail)
        result = await client.post(
            "/api/v1/assets/reference-images",
            headers=owner,
            data={"workspace_id": workspace, "brand_id": brand},
            files={"file": ("reference.png", data.getvalue(), "image/png")},
        )
        assert result.status_code == 503
        assert not storage.objects


@pytest.mark.anyio
async def test_upload_is_an_authorized_source_for_transform(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    _patch_worker_to_test_database(monkeypatch, application)
    data = BytesIO()
    Image.new("RGB", (32, 24), "red").save(data, format="PNG")

    class Artist:
        def execute(self, context: object) -> AgentExecutionResult:
            return AgentExecutionResult(
                output=ArtistOutput(visual_prompt="Preserve the subject"),
                prompt="Artist",
                prompt_template_id="artist",
                prompt_template_version="1",
                input_hash="a" * 64,
                output_hash="b" * 64,
                schema_name="ArtistOutput",
                schema_version="1",
                provider="test",
                model="test",
            )

    class Generator:
        def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
            assert request.source_image == data.getvalue()
            assert request.size == "1080x1350"
            output = BytesIO()
            Image.new("RGB", (1080, 1350), "red").save(output, format="PNG")
            return ImageGenerationResult(
                output.getvalue(), "image/png", 1080, 1350, "test", "test", {}
            )

    application.state.e2e_image_generator = Generator()
    monkeypatch.setattr(worker, "create_specialist_executor", lambda settings: Artist())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        owner, workspace = await _signup(client, "import-owner@example.com")
        outsider, _ = await _signup(client, "import-outsider@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=owner,
            json={"workspace_id": workspace, "name": "Import Brand"},
        )
        assert brand_response.status_code == 201
        brand = brand_response.json()["data"]["id"]
        imported = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand, "title": "Source"},
            files={"file": ("source.png", data.getvalue(), "image/png")},
        )
        assert imported.status_code == 201, imported.text
        content = imported.json()["data"]
        image = content["images"][0]
        assert image["generation_id"] is None and image["model"] is None and image["prompt"] is None
        assert (image["width"], image["height"], image["version_number"]) == (32, 24, 1)
        for image_format, mime_type in (("JPEG", "image/jpeg"), ("WEBP", "image/webp")):
            source = BytesIO()
            Image.new("RGB", (12, 12), "blue").save(source, format=image_format)
            response = await client.post(
                "/api/v1/contents/import-image",
                headers=owner,
                data={"brand_id": brand},
                files={"file": ("image", source.getvalue(), mime_type)},
            )
            assert response.status_code == 201, response.text
        invalid = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand},
            files={"file": ("bad.png", b"not an image", "image/png")},
        )
        assert invalid.status_code == 422
        mismatched = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand},
            files={"file": ("bad.jpg", data.getvalue(), "image/jpeg")},
        )
        assert mismatched.status_code == 422
        large = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand},
            files={"file": ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
        )
        assert large.status_code == 413
        denied = await client.post(
            "/api/v1/contents/import-image",
            headers=outsider,
            data={"brand_id": brand},
            files={"file": ("source.png", data.getvalue(), "image/png")},
        )
        assert denied.status_code == 404
        transform = await client.post(
            "/api/v1/generation-jobs",
            headers={**owner, "Idempotency-Key": "import-transform"},
            json={
                "brand_id": brand,
                "artifact_type": "IMAGE",
                "operation": "TRANSFORM",
                "briefing": "Adapt the image",
                "direction": "Preserve the subject",
                "source_content_id": content["id"],
                "source_image_id": image["id"],
                "destination_preset": "1080x1350",
            },
        )
        assert transform.status_code == 202, transform.text
        job_id = transform.json()["data"]["id"]
        worker.run_image_generation(job_id)
        pending = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=owner)
        assert pending.json()["data"]["scene_review"]["status"] == "PENDING"
        approved = await client.post(
            f"/api/v1/generation-jobs/{job_id}/scene-decision",
            headers=owner,
            json={"decision": "APPROVE"},
        )
        assert approved.status_code == 200
        worker.run_image_generation(job_id)
        completed = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=owner)
        result = completed.json()["data"]
        assert result["status"] == "COMPLETED"
        assert result["image"]["version_number"] == 2
        assert result["image"]["metadata"]["source_image_id"] == image["id"]


@pytest.mark.anyio
async def test_import_cleans_storage_when_database_write_fails(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    storage = application.state.e2e_storage
    data = BytesIO()
    Image.new("RGB", (12, 12), "blue").save(data, format="PNG")
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        owner, workspace = await _signup(client, "import-cleanup@example.com")
        brand_response = await client.post(
            "/api/v1/brands", headers=owner, json={"workspace_id": workspace, "name": "Brand"}
        )
        brand = brand_response.json()["data"]["id"]

        def fail(*args: object, **kwargs: object) -> None:
            raise RuntimeError("database failure")

        monkeypatch.setattr(SqlAlchemyContentRepository, "add_imported_image", fail)
        result = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand},
            files={"file": ("image.png", data.getvalue(), "image/png")},
        )
        assert result.status_code == 500
        assert not storage.objects
        contents = await client.get("/api/v1/contents", headers=owner)
        assert contents.json()["data"]["items"] == []


@pytest.mark.anyio
async def test_import_cleans_partial_upload_on_storage_failure(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    storage = application.state.e2e_storage
    data = BytesIO()
    Image.new("RGB", (12, 12), "blue").save(data, format="PNG")
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        owner, workspace = await _signup(client, "import-storage-failure@example.com")
        response = await client.post(
            "/api/v1/brands", headers=owner, json={"workspace_id": workspace, "name": "Brand"}
        )
        brand = response.json()["data"]["id"]
        upload = storage.upload

        def fail_after_write(request: object) -> None:
            upload(request)
            raise StorageUploadError("storage failure")

        monkeypatch.setattr(storage, "upload", fail_after_write)
        result = await client.post(
            "/api/v1/contents/import-image",
            headers=owner,
            data={"brand_id": brand},
            files={"file": ("image.png", data.getvalue(), "image/png")},
        )
        assert result.status_code == 500
        assert not storage.objects
        contents = await client.get("/api/v1/contents", headers=owner)
        assert contents.json()["data"]["items"] == []


@pytest.mark.anyio
async def test_image_migration_preserves_generated_version(e2e: tuple[object, object]) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        owner, workspace = await _signup(client, "migration-image@example.com")
        brand = (
            await client.post(
                "/api/v1/brands", headers=owner, json={"workspace_id": workspace, "name": "Brand"}
            )
        ).json()["data"]["id"]
        content = (
            await client.post(
                "/api/v1/contents",
                headers=owner,
                json={"workspace_id": workspace, "brand_id": brand, "type": "IMAGE"},
            )
        ).json()["data"]["id"]
        generation = (
            await client.post(
                "/api/v1/generations",
                headers=owner,
                json={
                    "workspace_id": workspace,
                    "content_id": content,
                    "brand_id": brand,
                    "type": "IMAGE",
                    "model": "test",
                    "prompt": "test",
                },
            )
        ).json()["data"]["id"]
    factory = application.state.e2e_factory
    with factory() as session:
        row = ImageRow(
            workspace_id=UUID(workspace),
            content_id=UUID(content),
            generation_id=UUID(generation),
            version_number=1,
            storage_path="users/test/image.png",
            public_url="https://example.com/image.png",
            mime_type="image/png",
            width=12,
            height=12,
            model="test",
            prompt="test",
            metadata_json={},
        )
        session.add(row)
        session.commit()
        image_id = row.id
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", application.state.e2e_settings.database_url)
    command.downgrade(config, "0005_content_text_versions")
    command.upgrade(config, "head")
    with factory() as session:
        restored = session.get(ImageRow, image_id)
        assert restored is not None
        assert restored.generation_id == UUID(generation)
        assert (restored.model, restored.prompt) == ("test", "test")
