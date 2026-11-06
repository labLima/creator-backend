from __future__ import annotations

import base64
import json
from collections.abc import Callable
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError
from PIL import Image

from creator.config import Settings
from creator.image_models import DEFAULT_OPENAI_IMAGE_MODEL
from creator.integrations.openai.image_generator import OpenAIImageGenerator
from creator.integrations.openai.image_reviewer import OpenAIMultimodalImageReviewer
from creator.services.ai.image_provider import (
    ImageGenerationRequest,
    ImageProviderAuthenticationError,
    ImageProviderBlockedError,
    ImageProviderError,
    ImageProviderInvalidResponseError,
    ImageProviderQuotaError,
    ImageProviderTimeoutError,
    ImageProviderTransientError,
)
from creator.services.ai.openai import OpenAILLMProvider
from creator.services.ai.provider import (
    LLMAuthenticationError,
    LLMInvalidResponseError,
    LLMQuotaError,
    LLMTimeoutError,
    LLMTransientError,
)
from creator.services.ai.reviewer import ImageReviewRequest

OPENAI_URL = "https://api.openai.com/v1/images/generations"


def _request() -> httpx.Request:
    return httpx.Request("POST", OPENAI_URL)


def png_bytes(size: tuple[int, int] = (2, 3)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color="red").save(output, format="PNG")
    return output.getvalue()


def noisy_png_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    width, height = size
    pixels = bytes(
        (x * 131 + y * 17 + x * y * 7) % 256
        for y in range(height)
        for x in range(width)
        for _ in range(3)
    )
    output = BytesIO()
    Image.frombytes("RGB", size, pixels).save(output, format="PNG")
    return output.getvalue()


def image_response(image: bytes) -> Any:
    encoded = base64.b64encode(image).decode("ascii")
    return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])


def api_status_error(status_code: int, *, code: str | None = None) -> APIStatusError:
    detail: dict[str, str] = {"message": "provider error"}
    if code is not None:
        detail["code"] = code
    body = {"error": detail}
    response = httpx.Response(status_code, request=_request(), json=body)
    return APIStatusError("provider error", response=response, body=body)


class FakeImagesAPI:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeResponsesAPI:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeOpenAIClient:
    def __init__(
        self,
        *,
        images: list[Any] | None = None,
        responses: list[Any] | None = None,
    ) -> None:
        self.images = FakeImagesAPI(images or [])
        self.responses = FakeResponsesAPI(responses or [])


def image_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openai_api_key": "test-openai-key",
        "openai_image_model": "gpt-image-2",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_generate_image_returns_decoded_png_with_dimensions_and_metadata() -> None:
    image = png_bytes((4, 5))
    client = FakeOpenAIClient(images=[image_response(image)])
    generator = OpenAIImageGenerator(image_settings(), client=client)

    result = generator.generate(ImageGenerationRequest(prompt="A red rectangle", size="1024x1024"))

    assert result.image_bytes == image
    assert result.mime_type == "image/png"
    assert (result.width, result.height) == (4, 5)
    assert result.model == "gpt-image-2"
    assert result.prompt == "A red rectangle"
    assert result.metadata["provider"] == "openai"
    assert result.metadata["source_model"] == "gpt-image-2"
    assert result.metadata["output_format"] == "png"
    assert result.metadata["requested_size"] == "1024x1024"
    assert client.images.calls[0]["model"] == "gpt-image-2"
    assert client.images.calls[0]["prompt"] == "A red rectangle"
    assert client.images.calls[0]["size"] == "1024x1024"
    assert client.images.calls[0]["output_format"] == "png"


def test_generate_image_uses_settings_default_model_when_request_omits_model() -> None:
    image = png_bytes((2, 3))
    client = FakeOpenAIClient(images=[image_response(image)])
    generator = OpenAIImageGenerator(
        image_settings(openai_image_model=DEFAULT_OPENAI_IMAGE_MODEL), client=client
    )

    result = generator.generate(ImageGenerationRequest(prompt="A red rectangle"))

    assert client.images.calls[0]["model"] == DEFAULT_OPENAI_IMAGE_MODEL
    assert result.model == DEFAULT_OPENAI_IMAGE_MODEL
    assert result.metadata["source_model"] == DEFAULT_OPENAI_IMAGE_MODEL


def test_generate_image_canonicalizes_legacy_request_model_at_the_provider_boundary() -> None:
    image = png_bytes((2, 3))
    client = FakeOpenAIClient(images=[image_response(image)])
    generator = OpenAIImageGenerator(
        image_settings(openai_image_model=DEFAULT_OPENAI_IMAGE_MODEL), client=client
    )

    generator.generate(
        ImageGenerationRequest(prompt="Legacy queued image", model="gpt-image-2.6-flare")
    )

    assert client.images.calls[0]["model"] == DEFAULT_OPENAI_IMAGE_MODEL


def test_generate_image_rejects_unsupported_requested_mime_type() -> None:
    client = FakeOpenAIClient()
    generator = OpenAIImageGenerator(image_settings(), client=client)

    with pytest.raises(ImageProviderInvalidResponseError):
        generator.generate(ImageGenerationRequest(prompt="logo", output_mime_type="image/gif"))

    assert client.images.calls == []


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(SimpleNamespace(data=[]), id="missing-data"),
        pytest.param(SimpleNamespace(data=[SimpleNamespace(b64_json=None)]), id="missing-b64-json"),
        pytest.param(SimpleNamespace(data=[SimpleNamespace(b64_json="")]), id="empty-b64-json"),
        pytest.param(
            SimpleNamespace(data=[SimpleNamespace(b64_json="not-valid-base64!!")]),
            id="malformed-base64",
        ),
        pytest.param(
            SimpleNamespace(
                data=[SimpleNamespace(b64_json=base64.b64encode(b"not an image").decode("ascii"))]
            ),
            id="decoded-bytes-are-not-an-image",
        ),
    ],
)
def test_generate_image_rejects_missing_or_invalid_image_payload(response: Any) -> None:
    client = FakeOpenAIClient(images=[response])
    generator = OpenAIImageGenerator(image_settings(), client=client)

    with pytest.raises(ImageProviderInvalidResponseError):
        generator.generate(ImageGenerationRequest(prompt="logo"))


@pytest.mark.parametrize(
    ("error_factory", "expected_error", "retryable"),
    [
        pytest.param(
            lambda: APITimeoutError(request=_request()),
            ImageProviderTimeoutError,
            True,
            id="timeout",
        ),
        pytest.param(
            lambda: APIConnectionError(request=_request()),
            ImageProviderTransientError,
            True,
            id="connection",
        ),
        pytest.param(
            lambda: api_status_error(401),
            ImageProviderAuthenticationError,
            False,
            id="status-401",
        ),
        pytest.param(
            lambda: api_status_error(429),
            ImageProviderQuotaError,
            True,
            id="status-429",
        ),
        pytest.param(
            lambda: api_status_error(500),
            ImageProviderTransientError,
            True,
            id="status-500",
        ),
        pytest.param(
            lambda: api_status_error(400, code="content_policy_violation"),
            ImageProviderBlockedError,
            False,
            id="status-400-content-policy",
        ),
    ],
)
def test_generate_image_maps_provider_failures(
    error_factory: Callable[[], Exception],
    expected_error: type[ImageProviderError],
    retryable: bool,
) -> None:
    client = FakeOpenAIClient(images=[error_factory()])
    generator = OpenAIImageGenerator(image_settings(), client=client)

    with pytest.raises(expected_error) as raised:
        generator.generate(ImageGenerationRequest(prompt="logo"))

    assert raised.value.retryable is retryable


@pytest.mark.parametrize(
    ("resolution", "aspect_ratio"),
    [
        ("1001x999", None),
        (None, "4:5"),
        (None, "9:16"),
        (None, "1:3"),
        (None, "3:1"),
    ],
)
def test_size_for_planning_returns_16_divisible_size_within_ratio_bounds(
    resolution: str | None, aspect_ratio: str | None
) -> None:
    size = OpenAIImageGenerator.size_for_planning(resolution=resolution, aspect_ratio=aspect_ratio)

    assert size is not None
    width, height = (int(value) for value in size.split("x"))
    assert width % 16 == 0, f"width {width} from {size} is not divisible by 16"
    assert height % 16 == 0, f"height {height} from {size} is not divisible by 16"
    assert 1 / 3 <= width / height <= 3, f"ratio from {size} is outside 1:3..3:1"


@pytest.mark.parametrize(
    ("resolution", "aspect_ratio"),
    [
        (None, "1:4"),
        (None, "4:1"),
        ("4000x1000", None),
        ("100x5000", None),
        ("not-a-resolution", None),
        (None, None),
    ],
)
def test_size_for_planning_rejects_invalid_or_out_of_bounds_inputs(
    resolution: str | None, aspect_ratio: str | None
) -> None:
    assert (
        OpenAIImageGenerator.size_for_planning(resolution=resolution, aspect_ratio=aspect_ratio)
        is None
    )


def test_oversized_base64_payload_is_rejected_before_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = noisy_png_bytes((64, 64))
    max_object_bytes = 1024
    assert len(image) > max_object_bytes

    decode_calls: list[tuple[Any, ...]] = []
    original_b64decode = base64.b64decode

    def tracking_b64decode(*args: Any, **kwargs: Any) -> bytes:
        decode_calls.append(args)
        return original_b64decode(*args, **kwargs)

    monkeypatch.setattr(base64, "b64decode", tracking_b64decode)
    client = FakeOpenAIClient(images=[image_response(image)])
    generator = OpenAIImageGenerator(
        image_settings(storage_max_object_bytes=max_object_bytes), client=client
    )

    with pytest.raises(ImageProviderInvalidResponseError):
        generator.generate(ImageGenerationRequest(prompt="large image"))

    assert decode_calls == [], "oversized payloads must be rejected before base64 decoding"


def test_payload_exceeding_decoded_size_limit_is_rejected() -> None:
    max_object_bytes = 32
    decoded = b"A" * (max_object_bytes + 1)
    encoded = base64.b64encode(decoded).decode("ascii")
    assert len(encoded) <= 4 * ((max_object_bytes + 2) // 3)
    client = FakeOpenAIClient(images=[SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])])
    generator = OpenAIImageGenerator(
        image_settings(storage_max_object_bytes=max_object_bytes), client=client
    )

    with pytest.raises(ImageProviderInvalidResponseError):
        generator.generate(ImageGenerationRequest(prompt="oversized decoded image"))


def test_payload_whose_decoded_image_fits_size_limit_is_accepted() -> None:
    image = png_bytes((2, 3))
    encoded = base64.b64encode(image)
    max_object_bytes = len(image) + 4
    assert len(image) <= max_object_bytes < len(encoded)

    client = FakeOpenAIClient(images=[image_response(image)])
    generator = OpenAIImageGenerator(
        image_settings(storage_max_object_bytes=max_object_bytes), client=client
    )

    result = generator.generate(ImageGenerationRequest(prompt="small image"))

    assert result.image_bytes == image


def llm_settings() -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key="test-openai-key",
        openai_text_model="gpt-5.5",
    )


def test_text_generation_returns_stripped_output_text() -> None:
    client = FakeOpenAIClient(responses=[SimpleNamespace(output_text="  Launch copy  ")])
    provider = OpenAILLMProvider(llm_settings(), client=client)

    assert provider.generate_text("Write a launch post", temperature=0.2) == "Launch copy"
    assert client.responses.calls[0]["model"] == "gpt-5.5"
    assert client.responses.calls[0]["input"] == "Write a launch post"
    assert client.responses.calls[0]["temperature"] == 0.2


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_text_generation_rejects_empty_output(output_text: str | None) -> None:
    client = FakeOpenAIClient(responses=[SimpleNamespace(output_text=output_text)])
    provider = OpenAILLMProvider(llm_settings(), client=client)

    with pytest.raises(LLMInvalidResponseError):
        provider.generate_text("Write a launch post")


@pytest.mark.parametrize(
    ("error_factory", "expected_error", "retryable"),
    [
        pytest.param(
            lambda: APITimeoutError(request=_request()),
            LLMTimeoutError,
            True,
            id="timeout",
        ),
        pytest.param(
            lambda: api_status_error(401),
            LLMAuthenticationError,
            False,
            id="status-401",
        ),
        pytest.param(
            lambda: api_status_error(429),
            LLMQuotaError,
            True,
            id="status-429",
        ),
        pytest.param(
            lambda: api_status_error(500),
            LLMTransientError,
            True,
            id="status-500",
        ),
    ],
)
def test_text_generation_maps_provider_failures(
    error_factory: Callable[[], Exception],
    expected_error: type[Exception],
    retryable: bool,
) -> None:
    client = FakeOpenAIClient(responses=[error_factory()])
    provider = OpenAILLMProvider(llm_settings(), client=client)

    with pytest.raises(expected_error) as raised:
        provider.generate_text("Write a launch post")

    assert raised.value.retryable is retryable


def reviewer_settings() -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key="test-openai-key",
        openai_reviewer_model="gpt-5.5",
    )


def review_request() -> ImageReviewRequest:
    return ImageReviewRequest(
        image_bytes=png_bytes(),
        mime_type="image/png",
        prompt="A red rectangle",
        briefing="Launch the summer collection",
        brand_context={"voice": "clear"},
    )


@pytest.mark.parametrize("fenced", [False, True], ids=["plain-json", "fenced-json"])
def test_reviewer_parses_valid_json_decision_and_feedback(fenced: bool) -> None:
    payload = {
        "decision": "REFINE",
        "score": 0.72,
        "feedback": ["Improve the crop"],
        "safety_issues": ["minor text legibility"],
    }
    text = json.dumps(payload)
    if fenced:
        text = f"```json\n{text}\n```"
    client = FakeOpenAIClient(responses=[SimpleNamespace(output_text=text)])
    reviewer = OpenAIMultimodalImageReviewer(reviewer_settings(), client=client)

    result = reviewer.review(review_request())

    assert result.decision == "REFINE"
    assert result.score == pytest.approx(0.72)
    assert result.feedback == ("Improve the crop",)
    assert result.safety_issues == ("minor text legibility",)
    assert result.provider == "openai"
    assert result.model == "gpt-5.5"
    assert client.responses.calls[0]["model"] == "gpt-5.5"


@pytest.mark.parametrize(
    "output_text",
    [
        pytest.param("", id="empty"),
        pytest.param("not json", id="not-json"),
        pytest.param('```json\n{"decision": \n```', id="malformed-fenced-json"),
        pytest.param(
            '{"decision": "MAYBE", "score": 0.5, "feedback": [], "safety_issues": []}',
            id="unknown-decision",
        ),
        pytest.param(
            '{"decision": "APPROVED", "score": 1.5, "feedback": [], "safety_issues": []}',
            id="score-out-of-range",
        ),
        pytest.param('{"score": 0.5}', id="missing-decision"),
    ],
)
def test_reviewer_rejects_invalid_json_and_values(output_text: str) -> None:
    client = FakeOpenAIClient(responses=[SimpleNamespace(output_text=output_text)])
    reviewer = OpenAIMultimodalImageReviewer(reviewer_settings(), client=client)

    with pytest.raises(ImageProviderInvalidResponseError):
        reviewer.review(review_request())
