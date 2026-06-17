"""Model provider interfaces and placeholder adapters."""

from researchinfra.models.adapters import (
    AnthropicProvider,
    LiteLLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
    VLLMProvider,
)
from researchinfra.models.base import ModelProvider, ModelProviderResult

__all__ = [
    "AnthropicProvider",
    "LiteLLMProvider",
    "ModelProvider",
    "ModelProviderResult",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "VLLMProvider",
]
