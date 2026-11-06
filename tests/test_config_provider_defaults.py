from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from creator.config import Settings
from creator.image_models import (
    DEFAULT_OPENAI_IMAGE_MODEL,
    KNOWN_OPENAI_IMAGE_MODELS,
)
from creator.integrations.openai.image_reviewer import OpenAIMultimodalImageReviewer
from creator.services.ai.factory import (
    UnconfiguredLLMProvider,
    create_image_reviewer,
    create_llm_provider,
)
from creator.services.ai.openai import OpenAILLMProvider
from creator.services.ai.provider import ProviderNotConfiguredError
from creator.services.ai.reviewer import (
    ImageReviewRequest,
    UnconfiguredMultimodalImageReviewer,
)


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_default_openai_image_model_is_known_and_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_name in ("OPENAI_IMAGE_MODEL", "OPENAI_TEXT_MODEL", "OPENAI_REVIEWER_MODEL"):
        monkeypatch.delenv(env_name, raising=False)

    settings = _settings()

    assert settings.openai_image_model == "gpt-image-2.5-sunburst"
    assert settings.openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL
    assert settings.openai_image_model in KNOWN_OPENAI_IMAGE_MODELS


def test_legacy_image_model_env_is_migrated_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2.6-flare")

    assert _settings().openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL


@pytest.mark.parametrize("blank_value", ["", "   "])
def test_blank_image_model_env_uses_default(
    monkeypatch: pytest.MonkeyPatch, blank_value: str
) -> None:
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", blank_value)

    assert _settings().openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL


def test_legacy_image_model_in_dotenv_is_migrated_to_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_IMAGE_MODEL=gpt-image-2.6-flare\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL


def test_explicit_image_model_env_override_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    assert _settings().openai_image_model == "gpt-image-2"


def test_default_text_and_reviewer_models_are_gpt_5_5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_name in ("OPENAI_IMAGE_MODEL", "OPENAI_TEXT_MODEL", "OPENAI_REVIEWER_MODEL"):
        monkeypatch.delenv(env_name, raising=False)

    settings = _settings()

    assert settings.openai_text_model == "gpt-5.5"
    assert settings.openai_reviewer_model == "gpt-5.5"


def test_create_image_reviewer_prefers_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "creator.integrations.openai.image_reviewer.create_openai_client",
        lambda settings: SimpleNamespace(),
    )

    reviewer = create_image_reviewer(
        _settings(openai_api_key="test-openai-key", gemini_api_key="test-gemini-key")
    )

    assert isinstance(reviewer, OpenAIMultimodalImageReviewer)


def test_create_image_reviewer_falls_back_to_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from creator.integrations.gemini.image_reviewer import GeminiMultimodalImageReviewer

    monkeypatch.setattr(
        "creator.integrations.gemini.image_reviewer.create_gemini_client",
        lambda settings: SimpleNamespace(),
    )

    reviewer = create_image_reviewer(
        _settings(openai_api_key=None, gemini_api_key="test-gemini-key")
    )

    assert isinstance(reviewer, GeminiMultimodalImageReviewer)


def test_create_image_reviewer_without_keys_is_unconfigured() -> None:
    reviewer = create_image_reviewer(_settings(openai_api_key=None, gemini_api_key=None))

    assert isinstance(reviewer, UnconfiguredMultimodalImageReviewer)


def test_create_llm_provider_with_openai_key_returns_openai_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "creator.services.ai.openai.create_openai_client",
        lambda settings: SimpleNamespace(),
    )

    provider = create_llm_provider(_settings(openai_api_key="test-openai-key"))

    assert isinstance(provider, OpenAILLMProvider)


def test_create_llm_provider_without_keys_fails_closed_on_use() -> None:
    provider = create_llm_provider(_settings(openai_api_key=None, gemini_api_key=None))

    assert isinstance(provider, UnconfiguredLLMProvider)
    with pytest.raises(ProviderNotConfiguredError):
        provider.generate_text("Write a launch post")


def _review_request() -> ImageReviewRequest:
    return ImageReviewRequest(
        image_bytes=b"image",
        mime_type="image/png",
        prompt="prompt",
        briefing="brief",
        brand_context={},
    )
