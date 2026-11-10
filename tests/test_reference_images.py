from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from PIL import Image

from creator.config import Settings
from creator.infrastructure.runtime import reference_images
from creator.services.ai.image_provider import ImageProviderInvalidResponseError


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (3, 2), "red").save(output, format="PNG")
    return output.getvalue()


def setup_resolution(monkeypatch: pytest.MonkeyPatch, records: list[Any], content: bytes) -> None:
    class UnitOfWork:
        def __enter__(self) -> UnitOfWork:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        class Assets:
            def get_for_user(self, *, user_id: object, asset_id: object) -> object | None:
                return next((record for record in records if record.id == asset_id), None)

        assets = Assets()

    class Storage:
        def download(self, _path: str, *, max_bytes: int) -> bytes:
            assert len(content) <= max_bytes
            return content

    monkeypatch.setattr(reference_images, "SqlAlchemyUnitOfWork", UnitOfWork)
    monkeypatch.setattr(reference_images, "create_storage_provider", lambda _settings: Storage())


def asset_record(*, workspace_id: object, brand_id: object, content: bytes) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        brand_id=brand_id,
        asset_type="REFERENCE_IMAGE",
        storage_path="private/reference.png",
        mime_type="image/png",
        byte_size=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        metadata={"reference_image_upload": True, "width": 3, "height": 2},
        deleted_at=None,
        created_at=datetime.now(UTC),
    )


def test_reference_resolver_preserves_client_order(monkeypatch: pytest.MonkeyPatch) -> None:
    content = png_bytes()
    workspace_id, brand_id, user_id = uuid4(), uuid4(), uuid4()
    first, second = (
        asset_record(workspace_id=workspace_id, brand_id=brand_id, content=content),
        asset_record(workspace_id=workspace_id, brand_id=brand_id, content=content),
    )
    setup_resolution(monkeypatch, [first, second], content)

    result = reference_images.resolve_reference_images(
        asset_ids=[str(second.id), str(first.id)],
        user_id=user_id,
        workspace_id=workspace_id,
        brand_id=brand_id,
        settings=Settings(),
    )

    assert [item.asset_id for item in result] == [str(second.id), str(first.id)]


@pytest.mark.parametrize("count", [5])
def test_reference_resolver_rejects_over_limit(count: int) -> None:
    with pytest.raises(ImageProviderInvalidResponseError):
        reference_images.resolve_reference_images(
            asset_ids=[str(uuid4()) for _ in range(count)],
            user_id=uuid4(),
            workspace_id=uuid4(),
            brand_id=uuid4(),
            settings=Settings(),
        )


def test_reference_resolver_rejects_cross_workspace_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    content = png_bytes()
    record = asset_record(workspace_id=uuid4(), brand_id=uuid4(), content=content)
    setup_resolution(monkeypatch, [record], content)

    with pytest.raises(ImageProviderInvalidResponseError):
        reference_images.resolve_reference_images(
            asset_ids=[str(record.id)],
            user_id=uuid4(),
            workspace_id=uuid4(),
            brand_id=record.brand_id,
            settings=Settings(),
        )


def test_reference_resolver_rejects_cross_brand_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    content = png_bytes()
    workspace_id = uuid4()
    record = asset_record(workspace_id=workspace_id, brand_id=uuid4(), content=content)
    setup_resolution(monkeypatch, [record], content)

    with pytest.raises(ImageProviderInvalidResponseError):
        reference_images.resolve_reference_images(
            asset_ids=[str(record.id)],
            user_id=uuid4(),
            workspace_id=workspace_id,
            brand_id=uuid4(),
            settings=Settings(),
        )


def test_reference_resolver_rejects_soft_deleted_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    content = png_bytes()
    record = asset_record(workspace_id=uuid4(), brand_id=uuid4(), content=content)
    record.deleted_at = datetime.now(UTC)
    setup_resolution(monkeypatch, [record], content)

    with pytest.raises(ImageProviderInvalidResponseError):
        reference_images.resolve_reference_images(
            asset_ids=[str(record.id)],
            user_id=uuid4(),
            workspace_id=record.workspace_id,
            brand_id=record.brand_id,
            settings=Settings(),
        )


def test_reference_resolver_rejects_changed_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    content = png_bytes()
    record = asset_record(workspace_id=uuid4(), brand_id=uuid4(), content=content)
    setup_resolution(monkeypatch, [record], b"changed")

    with pytest.raises(ImageProviderInvalidResponseError):
        reference_images.resolve_reference_images(
            asset_ids=[str(record.id)],
            user_id=uuid4(),
            workspace_id=record.workspace_id,
            brand_id=record.brand_id,
            settings=Settings(),
        )


def test_reference_resolver_sanitizes_storage_unavailability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = png_bytes()
    record = asset_record(workspace_id=uuid4(), brand_id=uuid4(), content=content)
    setup_resolution(monkeypatch, [record], content)

    class UnavailableStorage:
        def download(self, _path: str, *, max_bytes: int) -> bytes:
            raise RuntimeError("private bucket URL and credentials")

    monkeypatch.setattr(
        reference_images, "create_storage_provider", lambda _settings: UnavailableStorage()
    )
    with pytest.raises(ImageProviderInvalidResponseError) as raised:
        reference_images.resolve_reference_images(
            asset_ids=[str(record.id)],
            user_id=uuid4(),
            workspace_id=record.workspace_id,
            brand_id=record.brand_id,
            settings=Settings(),
        )
    assert str(raised.value) == "Reference image is unavailable"
    assert raised.value.__cause__ is None
