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
    return UnconfiguredMultimodalImageReviewer()
