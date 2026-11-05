from typing import Protocol


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a provider cannot safely be used."""


class LLMProviderError(RuntimeError):
    """Base error for text generation providers."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMAuthenticationError(LLMProviderError):
    pass


class LLMQuotaError(LLMProviderError):
    pass


class LLMTimeoutError(LLMProviderError):
    pass


class LLMBlockedContentError(LLMProviderError):
    pass


class LLMTransientError(LLMProviderError):
    pass


class LLMInvalidResponseError(LLMProviderError):
    pass


class LLMProvider(Protocol):
    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text for a validated prompt."""
