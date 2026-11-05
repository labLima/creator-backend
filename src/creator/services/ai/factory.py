from creator.config import Settings
from creator.services.ai.openai import OpenAILLMProvider
from creator.services.ai.provider import LLMProvider, ProviderNotConfiguredError
from creator.services.ai.reviewer import (
    MultimodalImageReviewer,
    UnconfiguredMultimodalImageReviewer,
)


class UnconfiguredLLMProvider:
    provider_name = "unconfigured"
    model = None

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        raise ProviderNotConfiguredError("LLM provider is not configured")


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.openai_api_key:
        return OpenAILLMProvider(settings)
    return UnconfiguredLLMProvider()


def create_image_reviewer(settings: Settings) -> MultimodalImageReviewer:
    if settings.openai_api_key:
        from creator.integrations.openai.image_reviewer import OpenAIMultimodalImageReviewer

        return OpenAIMultimodalImageReviewer(settings)
    if settings.gemini_api_key:
        # ADR-001 keeps Gemini as an optional legacy reviewer while OpenAI is
        # the active provider for generation.
        from creator.integrations.gemini.image_reviewer import GeminiMultimodalImageReviewer

        return GeminiMultimodalImageReviewer(settings)
    return UnconfiguredMultimodalImageReviewer()
