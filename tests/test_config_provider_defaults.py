from __future__ import annotations

from types import SimpleNamespace
from typing import get_args

import pytest
from openai.types.image_model import ImageModel

from creator.config import Settings
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


def test_default_openai_image_model_is_supported_by_the_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_name in ("OPENAI_IMAGE_MODEL", "OPENAI_TEXT_MODEL", "OPENAI_REVIEWER_MODEL"):
        monkeypatch.delenv(env_name, raising=False)

    settings = _settings()

    assert settings.openai_image_model == "gpt-image-2"
    assert settings.openai_image_model in get_args(ImageModel)


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
