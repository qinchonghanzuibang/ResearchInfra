"""Model provider interfaces and placeholder adapters."""

from researchinfra.models.adapters import (
    AnthropicProvider,
    LiteLLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
    VLLMProvider,
)
from researchinfra.models.base import (
    ModelProvider,
    ModelProviderConfigurationError,
    ModelProviderRequestError,
    ModelProviderResult,
)

__all__ = [
    "AnthropicProvider",
    "LiteLLMProvider",
    "ModelProvider",
    "ModelProviderConfigurationError",
    "ModelProviderRequestError",
    "ModelProviderResult",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "VLLMProvider",
]
