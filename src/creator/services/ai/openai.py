from __future__ import annotations

import logging
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError

from creator.config import Settings
from creator.integrations.openai.client import create_openai_client
from creator.services.ai.provider import (
    LLMAuthenticationError,
    LLMBlockedContentError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMQuotaError,
    LLMTimeoutError,
    LLMTransientError,
    ProviderNotConfiguredError,
)

logger = logging.getLogger(__name__)


class OpenAILLMProvider:
    provider_name = "openai"

    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        if not settings.openai_api_key:
            raise ProviderNotConfiguredError("OPENAI_API_KEY is required")
        self._settings = settings
        self._client = client if client is not None else create_openai_client(settings)
        self.model = settings.openai_text_model

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response = self._client.responses.create(
                model=self.model,
                input=prompt,
                temperature=temperature,
            )
        except Exception as error:
            provider_error = self._classify_error(error)
            logger.warning(
                "openai_text_generation_failure",
                extra={
                    "provider": self.provider_name,
                    "model": self.model,
                    "error_type": type(provider_error).__name__,
                    "retryable": provider_error.retryable,
                },
            )
            raise provider_error from error

        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise LLMInvalidResponseError("OpenAI response did not include text")
        logger.info(
            "openai_text_generation_success",
            extra={
                "provider": self.provider_name,
                "model": self.model,
                "text_size_chars": len(text),
            },
        )
        return text.strip()

    @staticmethod
    def _classify_error(error: Exception) -> LLMProviderError:
        if isinstance(error, LLMProviderError):
            return error
        if isinstance(error, APITimeoutError):
            return LLMTimeoutError("OpenAI request timed out", retryable=True)
        if isinstance(error, APIConnectionError):
            return LLMTransientError("OpenAI connection failed", retryable=True)
        if isinstance(error, APIStatusError):
            status = error.status_code
            if status in {401, 403}:
                return LLMAuthenticationError("OpenAI authentication failed")
            if status == 429:
                return LLMQuotaError("OpenAI quota or rate limit exceeded", retryable=True)
            if status in {408, 500, 502, 503, 504}:
                return LLMTransientError("OpenAI is temporarily unavailable", retryable=True)
            body = getattr(error, "body", None)
            detail = body.get("error", body) if isinstance(body, dict) else None
            code = detail.get("code") if isinstance(detail, dict) else None
            if code in {"content_policy_violation", "safety_violation"}:
                return LLMBlockedContentError("OpenAI blocked the text request")
            return LLMProviderError("OpenAI rejected the text request")
        return LLMProviderError("OpenAI text generation failed")
