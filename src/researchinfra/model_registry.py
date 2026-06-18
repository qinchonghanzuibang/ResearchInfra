"""Workspace-local model provider registry."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml

from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.schemas import ModelProviderConfig, ProviderKind, WorkspaceConfig


class ModelRegistryError(RuntimeError):
    """Raised when model registry configuration is invalid."""


MODEL_TASKS = ("reading", "writing", "reasoning", "cheap")
PROVIDER_KINDS: tuple[ProviderKind, ...] = (
    "openai-compatible",
    "litellm",
    "ollama",
    "anthropic",
    "openrouter",
    "vllm",
)


class ModelRegistry:
    """Read and update model provider configuration without storing secrets."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.config_path = self.workspace / ".researchinfra" / "workspace.yaml"

    def list(self) -> dict[str, Any]:
        """Return sanitized provider registry state."""

        config = self._load()
        return {
            "defaults": dict(config.model_defaults),
            "providers": [self._provider_row(provider) for provider in config.model_providers],
        }

    def set_default(self, *, task: str, provider_id: str, model: str) -> WorkspaceConfig:
        """Set a task-specific default model provider."""

        if task not in MODEL_TASKS:
            raise ModelRegistryError(f"Unsupported model task: {task}")
        config = self._load()
        providers = list(config.model_providers)
        index = self._find_provider_index(providers, provider_id)
        if index is None:
            if provider_id not in PROVIDER_KINDS:
                raise ModelRegistryError(
                    f"Unknown provider `{provider_id}`. Expected one of: "
                    f"{', '.join(PROVIDER_KINDS)}"
                )
            providers.append(
                ModelProviderConfig(
                    id=provider_id,
                    provider=provider_id,  # type: ignore[arg-type]
                    model=model,
                    enabled=True,
                )
            )
        else:
            current = providers[index]
            providers[index] = current.model_copy(update={"model": model, "enabled": True})

        defaults = dict(config.model_defaults)
        defaults[task] = provider_id
        updated = config.model_copy(
            update={"model_providers": providers, "model_defaults": defaults}
        )
        self._write(updated)
        return updated

    def test(self, *, task: str | None = None) -> dict[str, Any]:
        """Return a local readiness check for the default or first enabled provider."""

        if task is not None and task not in MODEL_TASKS:
            raise ModelRegistryError(f"Unsupported model task: {task}")
        config = self._load()
        provider = self._select_provider(config, task=task)
        status = self._status_for(provider)
        return {
            "task": task or "default",
            "provider_id": provider.id,
            "provider": provider.provider,
            "model": provider.model or "(not set)",
            **status,
        }

    def _load(self) -> WorkspaceConfig:
        if not self.config_path.exists():
            raise ModelRegistryError(
                f"Workspace config not found: {self.config_path}. "
                "Run `researchinfra init <workspace>` first."
            )
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ModelRegistryError(f"Invalid workspace config: {self.config_path}")
        return WorkspaceConfig.model_validate(data)

    def _write(self, config: WorkspaceConfig) -> None:
        self.config_path.write_text(
            yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )

    def _select_provider(self, config: WorkspaceConfig, *, task: str | None) -> ModelProviderConfig:
        provider_id = config.model_defaults.get(task or "") if task else None
        if provider_id:
            index = self._find_provider_index(config.model_providers, provider_id)
            if index is not None:
                return config.model_providers[index]
            raise ModelRegistryError(f"Default provider not found for task `{task}`: {provider_id}")

        enabled = [provider for provider in config.model_providers if provider.enabled]
        if enabled:
            return enabled[0]
        if config.model_providers:
            return config.model_providers[0]
        raise ModelRegistryError("No model providers are configured in this workspace.")

    def _find_provider_index(
        self, providers: list[ModelProviderConfig], provider_id: str
    ) -> int | None:
        for index, provider in enumerate(providers):
            if provider.id == provider_id or provider.provider == provider_id:
                return index
        return None

    def _provider_row(self, provider: ModelProviderConfig) -> dict[str, Any]:
        return {
            "id": provider.id,
            "provider": provider.provider,
            "enabled": provider.enabled,
            "model": provider.model or "",
            "base_url": provider.base_url or "",
            "environment": sorted(provider.environment),
            "parameters": sorted(provider.parameters),
        }

    def _status_for(self, provider: ModelProviderConfig) -> dict[str, Any]:
        if provider.provider == "openai-compatible":
            status = OpenAICompatibleProvider(provider).status()
            configured = bool(status["configured"]) and bool(provider.model or status["model"])
            instructions = (
                "Set OPENAI_API_KEY and optionally OPENAI_BASE_URL/OPENAI_MODEL, or set a "
                "model default with `researchinfra model set-default`."
            )
            return {
                "configured": configured,
                "api_key": status["api_key"],
                "base_url": status["base_url"],
                "can_execute": bool(status["configured"]),
                "message": "OpenAI-compatible configuration is ready."
                if status["configured"]
                else instructions,
            }

        if provider.provider == "litellm":
            configured = bool(provider.base_url or os.environ.get("LITELLM_BASE_URL"))
            return {
                "configured": configured,
                "can_execute": configured,
                "message": "Configure a LiteLLM proxy/base_url and model."
                if not configured
                else "LiteLLM gateway configuration is present.",
            }

        if provider.provider == "ollama":
            has_binary = shutil.which("ollama") is not None
            configured = has_binary and bool(provider.model)
            return {
                "configured": configured,
                "can_execute": configured,
                "message": (
                    "Install Ollama, start `ollama serve`, pull a model, then set the "
                    "ResearchInfra default."
                    if not configured
                    else "Ollama executable and model setting are present."
                ),
            }

        if provider.provider == "anthropic":
            configured = bool(os.environ.get("ANTHROPIC_API_KEY") and provider.model)
            return {
                "configured": configured,
                "api_key": "set" if os.environ.get("ANTHROPIC_API_KEY") else "missing",
                "can_execute": configured,
                "message": "Set ANTHROPIC_API_KEY and a model before using Anthropic.",
            }

        if provider.provider == "openrouter":
            configured = bool(os.environ.get("OPENROUTER_API_KEY") and provider.model)
            return {
                "configured": configured,
                "api_key": "set" if os.environ.get("OPENROUTER_API_KEY") else "missing",
                "can_execute": configured,
                "message": "Set OPENROUTER_API_KEY and a model before using OpenRouter.",
            }

        if provider.provider == "vllm":
            configured = bool(provider.base_url and provider.model)
            return {
                "configured": configured,
                "can_execute": configured,
                "message": "Run a vLLM OpenAI-compatible server and set base_url/model.",
            }

        return {
            "configured": False,
            "can_execute": False,
            "message": f"Unsupported provider kind: {provider.provider}",
        }
