from __future__ import annotations

from typing import Any

from openai import OpenAI

from creator.config import Settings
from creator.services.ai.provider import ProviderNotConfiguredError


def create_openai_client(settings: Settings) -> Any:
    if not settings.openai_api_key:
        raise ProviderNotConfiguredError("OPENAI_API_KEY is required")
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )
