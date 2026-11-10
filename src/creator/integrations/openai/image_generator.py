from __future__ import annotations

import base64
import logging
import re
from io import BytesIO
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError
from PIL import Image as PillowImage
from PIL import UnidentifiedImageError

from creator.config import Settings
from creator.image_models import canonical_image_model
from creator.integrations.openai.client import create_openai_client
from creator.services.ai.image_provider import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageProviderAuthenticationError,
    ImageProviderBlockedError,
    ImageProviderError,
    ImageProviderInvalidResponseError,
    ImageProviderQuotaError,
    ImageProviderTimeoutError,
    ImageProviderTransientError,
)

logger = logging.getLogger(__name__)

MIME_TO_OUTPUT_FORMAT = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
}
SUPPORTED_IMAGE_MIME_TYPES = frozenset(MIME_TO_OUTPUT_FORMAT)
TRANSIENT_STATUS_CODES = {408, 500, 502, 503, 504}
_TARGET_IMAGE_SIZES = frozenset({"1080x1080", "1080x1350", "1080x1920", "1920x1080"})


def _parse_size(value: str) -> tuple[int, int]:
    width_text, height_text = value.split("x", maxsplit=1)
    return int(width_text), int(height_text)


def _provider_compatible_size(value: str) -> str:
    if value not in _TARGET_IMAGE_SIZES:
        raise ImageProviderInvalidResponseError("Unsupported image transformation destination")
    width, height = _parse_size(value)
    provider_width = max(16, round(width / 16) * 16)
    provider_height = max(16, round(height / 16) * 16)
    return f"{provider_width}x{provider_height}"


def _resize_image(
    image_bytes: bytes, *, mime_type: str, size: tuple[int, int]
) -> tuple[bytes, int, int, str]:
    try:
        with PillowImage.open(BytesIO(image_bytes)) as image:
            image.load()
            resized = image.resize(size, PillowImage.Resampling.LANCZOS)
            output = BytesIO()
            image_format = {
                "image/png": "PNG",
                "image/jpeg": "JPEG",
                "image/webp": "WEBP",
            }[mime_type]
            if image_format == "JPEG" and resized.mode not in {"RGB", "L"}:
                resized = resized.convert("RGB")
            resized.save(output, format=image_format, quality=95)
    except (KeyError, OSError, UnidentifiedImageError) as error:
        raise ImageProviderInvalidResponseError("OpenAI returned invalid image bytes") from error
    return output.getvalue(), size[0], size[1], mime_type


class OpenAIImageGenerator:
    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else create_openai_client(settings)

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        output_format = MIME_TO_OUTPUT_FORMAT.get(request.output_mime_type)
        if output_format is None:
            raise ImageProviderInvalidResponseError("Unsupported requested image mime type")

        model = canonical_image_model(
            request.model, default_model=self._settings.openai_image_model
        )
        size = (
            request.size
            or self.size_for_planning(
                resolution=request.resolution,
                aspect_ratio=request.aspect_ratio,
            )
            or "auto"
        )
        final_size = size if request.source_image is not None else None
        provider_size = _provider_compatible_size(final_size) if final_size else size
        try:
            if request.source_image is not None:
                extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
                    request.source_image_mime_type or ""
                )
                if extension is None:
                    raise ImageProviderInvalidResponseError("Unsupported source image MIME type")
                inputs = [(f"source.{extension}", request.source_image)]
                for reference in request.reference_images:
                    reference_extension = {
                        "image/png": "png",
                        "image/jpeg": "jpg",
                        "image/webp": "webp",
                    }.get(reference.mime_type)
                    if reference_extension is None:
                        raise ImageProviderInvalidResponseError(
                            "Unsupported reference image MIME type"
                        )
                    inputs.append((f"reference.{reference_extension}", reference.content))
                edit_options: dict[str, Any] = {
                    "model": model,
                    "prompt": request.prompt,
                    "image": inputs[0] if len(inputs) == 1 else inputs,
                    "size": provider_size,
                    "quality": "auto",
                    "output_format": output_format,
                }
                if not model.lower().startswith("gpt-image-2"):
                    edit_options["input_fidelity"] = "high"
                response = self._client.images.edit(**edit_options)
            elif request.reference_images:
                inputs = []
                for reference in request.reference_images:
                    reference_extension = {
                        "image/png": "png",
                        "image/jpeg": "jpg",
                        "image/webp": "webp",
                    }.get(reference.mime_type)
                    if reference_extension is None:
                        raise ImageProviderInvalidResponseError(
                            "Unsupported reference image MIME type"
                        )
                    inputs.append((f"reference.{reference_extension}", reference.content))
                response = self._client.images.edit(
                    model=model,
                    prompt=request.prompt,
                    image=inputs,
                    size=size,
                    quality="auto",
                    output_format=output_format,
                )
            else:
                response = self._client.images.generate(
                    model=model,
                    prompt=request.prompt,
                    size=size,
                    quality="auto",
                    output_format=output_format,
                )
        except Exception as error:
            raise self._classify_error(error) from error

        data = getattr(response, "data", None)
        encoded_image = getattr(data[0], "b64_json", None) if data else None
        if not isinstance(encoded_image, str) or not encoded_image:
            raise ImageProviderInvalidResponseError("OpenAI response did not include image bytes")

        max_bytes = self._settings.storage_max_object_bytes
        max_encoded_bytes = 4 * ((max_bytes + 2) // 3)
        if len(encoded_image) > max_encoded_bytes:
            raise ImageProviderInvalidResponseError("OpenAI returned an oversized image")

        try:
            image_bytes = base64.b64decode(encoded_image, validate=True)
        except ValueError as error:
            raise ImageProviderInvalidResponseError(
                "OpenAI returned invalid image bytes"
            ) from error
        if len(image_bytes) > max_bytes:
            raise ImageProviderInvalidResponseError("OpenAI returned an oversized image")
        try:
            width, height, mime_type = self._inspect_image(image_bytes, request.output_mime_type)
        except (UnidentifiedImageError, PillowImage.DecompressionBombError) as error:
            raise ImageProviderInvalidResponseError(
                "OpenAI returned invalid image bytes"
            ) from error

        if final_size and (width, height) != _parse_size(provider_size):
            raise ImageProviderInvalidResponseError(
                "OpenAI returned dimensions different from the requested render size"
            )

        metadata = {
            "provider": "openai",
            "source_model": model,
            "output_format": output_format,
            "requested_size": final_size or size,
            "provider_render_size": provider_size,
            **request.metadata,
        }
        if final_size and (width, height) != _parse_size(final_size):
            image_bytes, width, height, mime_type = _resize_image(
                image_bytes,
                mime_type=mime_type,
                size=_parse_size(final_size),
            )
            metadata["dimensions_normalized_without_crop"] = True
            if len(image_bytes) > max_bytes:
                raise ImageProviderInvalidResponseError(
                    "Normalized image exceeds the configured storage limit"
                )
        logger.info(
            "openai_image_generation_success",
            extra={
                "provider": "openai",
                "model": model,
                "mime_type": mime_type,
                "image_size_bytes": len(image_bytes),
            },
        )
        return ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            width=width,
            height=height,
            model=model,
            prompt=request.prompt,
            metadata=metadata,
        )

    def _inspect_image(self, image_bytes: bytes, requested_mime_type: str) -> tuple[int, int, str]:
        try:
            with PillowImage.open(BytesIO(image_bytes)) as image:
                width, height = image.size
                detected_mime_type = PillowImage.MIME.get(image.format or "", requested_mime_type)
                image.verify()
        except (UnidentifiedImageError, OSError) as error:
            raise ImageProviderInvalidResponseError(
                "OpenAI returned invalid image bytes"
            ) from error
        if width <= 0 or height <= 0 or detected_mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise ImageProviderInvalidResponseError("OpenAI returned unsupported image bytes")
        return width, height, detected_mime_type

    @staticmethod
    def _classify_error(error: Exception) -> ImageProviderError:
        if isinstance(error, ImageProviderError):
            return error
        if isinstance(error, APITimeoutError):
            return ImageProviderTimeoutError("OpenAI image request timed out", retryable=True)
        if isinstance(error, APIConnectionError):
            return ImageProviderTransientError("OpenAI image connection failed", retryable=True)
        if isinstance(error, APIStatusError):
            status = error.status_code
            if status in {401, 403}:
                return ImageProviderAuthenticationError("OpenAI image authentication failed")
            if status == 429:
                return ImageProviderQuotaError(
                    "OpenAI image quota or rate limit exceeded", retryable=True
                )
            if status in TRANSIENT_STATUS_CODES:
                return ImageProviderTransientError(
                    "OpenAI image provider is temporarily unavailable", retryable=True
                )
            if OpenAIImageGenerator._error_code(error) in {
                "content_policy_violation",
                "safety_violation",
            }:
                return ImageProviderBlockedError("OpenAI blocked the image request")
            return ImageProviderError("OpenAI rejected the image request")
        if isinstance(error, (TimeoutError, APITimeoutError)):
            return ImageProviderTimeoutError("OpenAI image request timed out", retryable=True)
        if isinstance(error, (APIConnectionError, ConnectionError)):
            return ImageProviderTransientError("OpenAI image connection failed", retryable=True)
        return ImageProviderError("OpenAI image generation failed")

    @staticmethod
    def size_for_planning(*, resolution: str | None, aspect_ratio: str | None) -> str | None:
        if resolution:
            match = re.fullmatch(r"\s*(\d{2,4})\s*[x×]\s*(\d{2,4})\s*", resolution.lower())
            if match:
                width, height = (int(value) // 16 * 16 for value in match.groups())
                if 16 <= width <= 3840 and 16 <= height <= 2160:
                    ratio = width / height
                    if 1 / 3 <= ratio <= 3:
                        return f"{width}x{height}"
        if aspect_ratio:
            match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\s*", aspect_ratio)
            if match:
                numerator, denominator = (float(value) for value in match.groups())
                if numerator > 0 and denominator > 0:
                    ratio = numerator / denominator
                    if 1 / 3 <= ratio <= 3:
                        long_edge = 1536
                        if ratio >= 1:
                            width, height = long_edge, int(long_edge / ratio) // 16 * 16
                        else:
                            width, height = int(long_edge * ratio) // 16 * 16, long_edge
                        return f"{width}x{height}"
        return None

    @staticmethod
    def _error_code(error: APIStatusError) -> str | None:
        body = getattr(error, "body", None)
        if not isinstance(body, dict):
            return None
        detail = body.get("error", body)
        if isinstance(detail, dict):
            code = detail.get("code")
            if isinstance(code, str):
                return code
        return None
