"""Placeholder model provider adapters."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from researchinfra.models.base import (
    ModelProvider,
    ModelProviderConfigurationError,
    ModelProviderRequestError,
    ModelProviderResult,
)

_SECRET_ENVIRONMENT_VARIABLES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([^\s,;\"'}]+)"),
    re.compile(r"(?i)(\bbearer\s+)([^\s,;\"'}]+)"),
    re.compile(
        r"(?i)([\"']?(?:api[_-]?key|token|access[_-]?token|secret|authorization)"
        r"[\"']?\s*[:=]\s*[\"']?)([^\s,}\]\"']+)"
    ),
)


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

    def is_configured(self) -> bool:
        """Return whether the provider has the minimum environment config."""

        return bool(os.environ.get("OPENAI_API_KEY"))

    def status(self) -> dict[str, str | bool]:
        """Return non-secret provider status for CLI checks."""

        base_url = os.environ.get("OPENAI_BASE_URL") or self.config.base_url
        model = os.environ.get("OPENAI_MODEL") or self.config.model
        return {
            "configured": self.is_configured(),
            "provider": "openai-compatible",
            "base_url": redact_sensitive_text(base_url or "https://api.openai.com/v1"),
            "model": model or "(OPENAI_MODEL not set)",
            "api_key": "set" if self.is_configured() else "missing",
        }

    def complete(self, prompt: str, **kwargs: Any) -> ModelProviderResult:
        """Call an OpenAI-compatible chat completions endpoint."""

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ModelProviderConfigurationError(
                "OPENAI_API_KEY is not set. Set OPENAI_API_KEY, optionally "
                "OPENAI_BASE_URL and OPENAI_MODEL, or rerun with --dry-run."
            )

        base_url = (
            os.environ.get("OPENAI_BASE_URL") or self.config.base_url or "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.environ.get("OPENAI_MODEL") or self.config.model or "gpt-4o-mini"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.pop("temperature", 0.2),
            **kwargs,
        }
        request = Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ModelProviderRequestError(
                f"OpenAI-compatible API request failed with HTTP {exc.code}. "
                "Check the endpoint, credentials, and request configuration."
            ) from exc
        except URLError as exc:
            raise ModelProviderRequestError(
                "OpenAI-compatible API request failed due to a network error. "
                "Check the endpoint and network configuration."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelProviderRequestError(
                "OpenAI-compatible API returned an invalid response. "
                "Check the endpoint and response format."
            ) from exc

        text = _extract_chat_text(data)
        return ModelProviderResult(text=text, raw=data)


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


def _extract_chat_text(data: dict[str, Any]) -> str | None:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        return content if isinstance(content, str) else None
    text = first.get("text")
    return text if isinstance(text, str) else None


def redact_sensitive_text(value: str) -> str:
    """Redact secrets before a provider value is exposed to a caller or CLI."""

    redacted = value
    for environment_name in _SECRET_ENVIRONMENT_VARIABLES:
        secret = os.environ.get(environment_name)
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted
