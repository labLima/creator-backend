from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from creator.config import Settings
from creator.image_models import canonical_image_model


class ImageProviderError(RuntimeError):
    """Base error for image generation providers."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ImageProviderAuthenticationError(ImageProviderError):
    pass


class ImageProviderQuotaError(ImageProviderError):
    pass


class ImageProviderTimeoutError(ImageProviderError):
    pass


class ImageProviderBlockedError(ImageProviderError):
    pass


class ImageProviderTransientError(ImageProviderError):
    pass


class ImageProviderInvalidResponseError(ImageProviderError):
    pass


def normalize_image_model(requested_model: str | None, *, default_model: str) -> str:
    """Map legacy Gemini and retired OpenAI image models to the configured model."""
    return canonical_image_model(requested_model, default_model=default_model)


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    prompt: str
    model: str | None = None
    output_mime_type: str = "image/png"
    metadata: dict[str, object] = field(default_factory=dict)
    size: str | None = None
    aspect_ratio: str | None = None
    resolution: str | None = None
    source_image: bytes | None = None
    source_image_mime_type: str | None = None


@dataclass(frozen=True, slots=True)
class ImageGenerationResult:
    image_bytes: bytes
    mime_type: str
    width: int
    height: int
    model: str
    prompt: str
    metadata: dict[str, object]


class ImageGenerator(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...


def create_image_generator(settings: Settings) -> ImageGenerator:
    from creator.integrations.openai.image_generator import OpenAIImageGenerator

    return OpenAIImageGenerator(settings)
