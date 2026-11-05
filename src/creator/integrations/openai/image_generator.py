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


class OpenAIImageGenerator:
    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client if client is not None else create_openai_client(settings)

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        output_format = MIME_TO_OUTPUT_FORMAT.get(request.output_mime_type)
        if output_format is None:
            raise ImageProviderInvalidResponseError("Unsupported requested image mime type")

        model = request.model or self._settings.openai_image_model
        size = (
            request.size
            or self.size_for_planning(
                resolution=request.resolution,
                aspect_ratio=request.aspect_ratio,
            )
            or "auto"
        )
        try:
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

        metadata = {
            "provider": "openai",
            "source_model": model,
            "output_format": output_format,
            "requested_size": size,
            **request.metadata,
        }
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
