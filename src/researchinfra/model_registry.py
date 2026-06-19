"""Workspace-local model provider registry."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.schemas import ModelProviderConfig, ProviderKind, WorkspaceConfig
from researchinfra.workspace import WorkspaceError, load_workspace_config


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
        """Return a local readiness check for the provider a runtime call would use."""

        if task is not None and task not in MODEL_TASKS:
            raise ModelRegistryError(f"Unsupported model task: {task}")
        config = self._load()
        provider = self._select_execution_provider(config, task=task)
        if provider is None:
            task_label = task or "default"
            return {
                "task": task_label,
                "provider_id": "(none)",
                "provider": "(none)",
                "model": "(not set)",
                "configured": False,
                "can_execute": False,
                "message": "No enabled model default is configured. Use "
                "`researchinfra model set-default` before running model-invoking commands.",
            }
        status = self._status_for(provider)
        return {
            "task": task or "default",
            "provider_id": provider.id,
            "provider": provider.provider,
            "model": provider.model or "(not set)",
            **status,
        }

    def provider_for_execution(self, *, task: str) -> ModelProviderConfig | None:
        """Return an explicitly configured provider for a runtime task, if one exists."""

        if task not in MODEL_TASKS:
            raise ModelRegistryError(f"Unsupported model task: {task}")
        return self._select_execution_provider(self._load(), task=task)

    def _load(self) -> WorkspaceConfig:
        try:
            return load_workspace_config(self.workspace)
        except WorkspaceError as exc:
            raise ModelRegistryError(str(exc)) from exc

    def _write(self, config: WorkspaceConfig) -> None:
        import yaml

        self.config_path.write_text(
            yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )

    def _select_execution_provider(
        self, config: WorkspaceConfig, *, task: str | None
    ) -> ModelProviderConfig | None:
        provider_id = config.model_defaults.get(task) if task else None
        if provider_id:
            index = self._find_provider_index(config.model_providers, provider_id)
            if index is not None:
                return config.model_providers[index]
            raise ModelRegistryError(f"Default provider not found for task `{task}`: {provider_id}")

        enabled = [provider for provider in config.model_providers if provider.enabled]
        if enabled:
            return enabled[0]
        return None

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
            instructions = (
                "Set OPENAI_API_KEY and optionally OPENAI_BASE_URL/OPENAI_MODEL, or set a "
                "model default with `researchinfra model set-default`."
            )
            return {
                "configured": bool(status["configured"]),
                "api_key": status["api_key"],
                "base_url": status["base_url"],
                "model": status["model"],
                "can_execute": bool(status["configured"]),
                "message": "OpenAI-compatible configuration is ready."
                if status["configured"]
                else instructions,
            }

        if provider.provider == "litellm":
            configured = bool(
                (provider.base_url or os.environ.get("LITELLM_BASE_URL")) and provider.model
            )
            return {
                "configured": configured,
                "can_execute": False,
                "message": "Configure a LiteLLM proxy/base_url and model."
                if not configured
                else "LiteLLM is configured but has no executable adapter in ResearchInfra 0.1. "
                "Use an OpenAI-compatible endpoint or add a LiteLLM adapter.",
            }

        if provider.provider == "ollama":
            configured = bool(provider.model)
            return {
                "configured": configured,
                "can_execute": False,
                "message": "Install Ollama, start `ollama serve`, pull a model, and set a model "
                "default. ResearchInfra 0.1 has no executable Ollama adapter yet."
                if not configured
                else "Ollama is configured but has no executable adapter in ResearchInfra 0.1. "
                "Use an OpenAI-compatible endpoint or add an Ollama adapter.",
            }

        if provider.provider == "anthropic":
            configured = bool(os.environ.get("ANTHROPIC_API_KEY") and provider.model)
            return {
                "configured": configured,
                "api_key": "set" if os.environ.get("ANTHROPIC_API_KEY") else "missing",
                "can_execute": False,
                "message": "Set ANTHROPIC_API_KEY and a model. ResearchInfra 0.1 has no "
                "executable Anthropic adapter yet."
                if not configured
                else "Anthropic is configured but has no executable adapter in ResearchInfra 0.1. "
                "Use an OpenAI-compatible endpoint or add an Anthropic adapter.",
            }

        if provider.provider == "openrouter":
            configured = bool(os.environ.get("OPENROUTER_API_KEY") and provider.model)
            return {
                "configured": configured,
                "api_key": "set" if os.environ.get("OPENROUTER_API_KEY") else "missing",
                "can_execute": False,
                "message": "Set OPENROUTER_API_KEY and a model. ResearchInfra 0.1 has no "
                "executable OpenRouter adapter yet."
                if not configured
                else "OpenRouter is configured but has no executable adapter in ResearchInfra 0.1. "
                "Use an OpenAI-compatible endpoint or add an OpenRouter adapter.",
            }

        if provider.provider == "vllm":
            configured = bool(provider.base_url and provider.model)
            return {
                "configured": configured,
                "can_execute": False,
                "message": "Run a vLLM OpenAI-compatible server and set base_url/model. "
                "ResearchInfra 0.1 has no dedicated vLLM adapter yet."
                if not configured
                else "vLLM is configured but has no executable adapter in ResearchInfra 0.1. "
                "Use an OpenAI-compatible provider config for the server endpoint.",
            }

        return {
            "configured": False,
            "can_execute": False,
            "message": f"Unsupported provider kind: {provider.provider}",
        }
