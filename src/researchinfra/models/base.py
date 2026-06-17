"""Model provider protocol for agent-agnostic inference routing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from researchinfra.schemas import ModelProviderConfig


@dataclass(frozen=True)
class ModelProviderResult:
    """Provider response envelope used by future concrete adapters."""

    text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    """Base class for model providers.

    Provider adapters should keep credentials outside workspace files and read
    secret material from the environment or the caller's process context.
    """

    def __init__(self, config: ModelProviderConfig) -> None:
        self.config = config

    @property
    def provider_id(self) -> str:
        return self.config.id

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> ModelProviderResult:
        """Return a completion for a prompt."""
