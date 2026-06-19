"""Resolve workspace model defaults into honest runtime providers."""

from __future__ import annotations

from pathlib import Path

from researchinfra.model_registry import ModelRegistry, ModelRegistryError
from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.models.base import ModelProvider, ModelProviderConfigurationError


class ModelDispatcher:
    """Route model-invoking workflows through their workspace task default."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry = ModelRegistry(self.workspace)

    def provider_for_task(self, task: str) -> ModelProvider | None:
        """Return a concrete provider, or None when no provider is configured."""

        try:
            config = self.registry.provider_for_execution(task=task)
        except ModelRegistryError as exc:
            raise ModelProviderConfigurationError(str(exc)) from exc
        if config is None:
            return None
        if config.provider == "openai-compatible":
            return OpenAICompatibleProvider(config)
        raise ModelProviderConfigurationError(
            f"The `{config.provider}` provider is selected for `{task}`, but ResearchInfra 0.1 "
            "does not include an executable adapter for it. Configure an `openai-compatible` "
            "provider for this task, use --dry-run, or add the provider adapter."
        )


def task_for_skill_category(category: str) -> str:
    """Map a skill category to a stable model-default task tier."""

    if category == "reading":
        return "reading"
    if category in {"writing", "latex", "submission"}:
        return "writing"
    if category in {"ideation", "project-planning", "experiment-planning", "reviewing", "agents"}:
        return "reasoning"
    return "cheap"
