"""Placeholder model provider adapters."""

from __future__ import annotations

from typing import Any

from researchinfra.models.base import ModelProvider, ModelProviderResult


class PlaceholderModelProvider(ModelProvider):
    """Provider base that documents unsupported execution."""

    display_name = "placeholder"

    def complete(self, prompt: str, **kwargs: Any) -> ModelProviderResult:
        return ModelProviderResult(
            text=None,
            raw={
                "provider": self.config.provider,
                "message": (
                    f"{self.display_name} provider is an extension point. "
                    "Configure a concrete adapter before inference."
                ),
                "prompt_length": len(prompt),
                "parameters": kwargs,
            },
        )


class OpenAICompatibleProvider(PlaceholderModelProvider):
    display_name = "OpenAI-compatible API"


class LiteLLMProvider(PlaceholderModelProvider):
    display_name = "LiteLLM"


class OllamaProvider(PlaceholderModelProvider):
    display_name = "Ollama"


class AnthropicProvider(PlaceholderModelProvider):
    display_name = "Anthropic"


class OpenRouterProvider(PlaceholderModelProvider):
    display_name = "OpenRouter"


class VLLMProvider(PlaceholderModelProvider):
    display_name = "vLLM"
