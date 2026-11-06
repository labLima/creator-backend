from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from creator.config import Settings
from creator.image_models import (
    DEFAULT_OPENAI_IMAGE_MODEL,
    canonical_image_model,
)
from creator.integrations.openai.image_generator import OpenAIImageGenerator
from creator.services.ai.image_provider import (
    ImageGenerationRequest,
    normalize_image_model,
)

NEW_DEFAULT = "gpt-image-2.5-sunburst"
SNAPSHOT = "gpt-image-2.5-sunburst-2026-09-08"


def png_bytes(size: tuple[int, int] = (2, 3)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color="red").save(output, format="PNG")
    return output.getvalue()


class FakeImagesAPI:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        encoded = base64.b64encode(png_bytes()).decode("ascii")
        return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.images = FakeImagesAPI()


@pytest.mark.parametrize(
    ("requested_model", "expected_model"),
    [
        pytest.param(None, NEW_DEFAULT, id="none"),
        pytest.param("", NEW_DEFAULT, id="empty"),
        pytest.param(" \t\n ", NEW_DEFAULT, id="whitespace-only"),
        pytest.param("gpt-image-2.6-flare", NEW_DEFAULT, id="legacy-openai"),
        pytest.param("GEMINI-2.5-flash-image", NEW_DEFAULT, id="uppercase-gemini"),
        pytest.param("imagen-3.0", NEW_DEFAULT, id="legacy-imagen"),
        pytest.param("gpt-image-2", "gpt-image-2", id="explicit-prior-openai"),
        pytest.param(NEW_DEFAULT, NEW_DEFAULT, id="new-default"),
        pytest.param(SNAPSHOT, SNAPSHOT, id="new-default-snapshot"),
        pytest.param("  custom-image-model  ", "custom-image-model", id="custom-trimmed"),
    ],
)
def test_canonical_image_model_maps_legacy_values_and_preserves_supported_values(
    requested_model: str | None, expected_model: str
) -> None:
    assert canonical_image_model(requested_model) == expected_model


@pytest.mark.parametrize(
    ("dotenv_value", "expected_model"),
    [
        pytest.param("gpt-image-2.6-flare", NEW_DEFAULT, id="legacy-openai"),
        pytest.param("gpt-image-2", "gpt-image-2", id="explicit-prior-openai"),
    ],
)
def test_settings_loads_image_model_from_real_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dotenv_value: str,
    expected_model: str,
) -> None:
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"OPENAI_IMAGE_MODEL={dotenv_value}\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.openai_image_model == expected_model


def test_queued_work_item_legacy_model_is_normalized_before_openai_call() -> None:
    settings = Settings(_env_file=None)
    queued_work_item = SimpleNamespace(model="gpt-image-2.6-flare")
    normalized_model = normalize_image_model(
        queued_work_item.model,
        default_model=settings.openai_image_model,
    )
    client = FakeOpenAIClient()
    generator = OpenAIImageGenerator(settings, client=client)

    result = generator.generate(
        ImageGenerationRequest(prompt="legacy queued image", model=normalized_model)
    )

    assert client.images.calls[0]["model"] == NEW_DEFAULT
    assert result.model == NEW_DEFAULT
    assert result.metadata["source_model"] == NEW_DEFAULT


@pytest.mark.parametrize(
    ("request_model", "expected_model"),
    [
        pytest.param(None, NEW_DEFAULT, id="omitted-model-uses-settings-default"),
        pytest.param("gpt-image-2", "gpt-image-2", id="explicit-model-is-preserved"),
    ],
)
def test_openai_image_generator_resolves_request_model(
    request_model: str | None, expected_model: str
) -> None:
    settings = Settings(_env_file=None)
    client = FakeOpenAIClient()
    generator = OpenAIImageGenerator(settings, client=client)

    result = generator.generate(ImageGenerationRequest(prompt="image", model=request_model))

    assert settings.openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL
    assert client.images.calls[0]["model"] == expected_model
    assert result.model == expected_model
    assert result.metadata["source_model"] == expected_model
