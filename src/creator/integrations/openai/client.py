from __future__ import annotations

from typing import Any

from openai import OpenAI

from creator.config import Settings
from creator.services.ai.provider import ProviderNotConfiguredError


def sampling_options(model: str, temperature: float) -> dict[str, float]:
    # Reasoning models reject temperature at their default reasoning effort.
    if model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")):
        return {}
    return {"temperature": temperature}


def create_openai_client(settings: Settings) -> Any:
    if not settings.openai_api_key:
        raise ProviderNotConfiguredError("OPENAI_API_KEY is required")
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )
