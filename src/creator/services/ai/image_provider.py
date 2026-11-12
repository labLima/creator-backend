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
    """Map legacy Gemini and legacy OpenAI image models to the configured model."""
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
    reference_images: tuple[ImageInput, ...] = ()


@dataclass(frozen=True, slots=True)
class ImageInput:
    content: bytes
    mime_type: str
    asset_id: str | None = None
    checksum_sha256: str | None = None


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


@dataclass(frozen=True, slots=True)
class ImageEditRequest:
    """Provider-neutral edit of an authorized, immutable source image."""

    source_image: bytes
    source_mime_type: str
    destination_size: str
    direction: str
    brand_context: dict[str, str] = field(default_factory=dict)
    output_mime_type: str = "image/png"
    model: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    reference_images: tuple[ImageInput, ...] = ()


class ImageEditor(Protocol):
    def edit(self, request: ImageEditRequest) -> ImageGenerationResult: ...


class ImageGenerationEditor:
    """Bridge image transformation into existing provider image adapters."""

    def __init__(self, generator: ImageGenerator) -> None:
        self._generator = generator

    def edit(self, request: ImageEditRequest) -> ImageGenerationResult:
        prompt = (
            f"{request.direction}\n\nAdapt the supplied source image to exactly "
            f"{request.destination_size} pixels. Preserve subject scale and visual intent. "
            "Expand or reorganize the composition generatively; do not remove important "
            "content. Exact text and logos must be handled by deterministic composition "
            "and human review.\n\nBrand context: "
            + "; ".join(f"{key}: {value}" for key, value in request.brand_context.items())
        )
        return self._generator.generate(
            ImageGenerationRequest(
                prompt=prompt,
                model=request.model,
                output_mime_type=request.output_mime_type,
                metadata=request.metadata,
                size=request.destination_size,
                source_image=request.source_image,
                source_image_mime_type=request.source_mime_type,
                reference_images=request.reference_images,
            )
        )


def create_image_generator(settings: Settings) -> ImageGenerator:
    from creator.integrations.openai.image_generator import OpenAIImageGenerator

    return OpenAIImageGenerator(settings)
