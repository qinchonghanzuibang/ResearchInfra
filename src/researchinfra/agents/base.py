"""Agent backend protocol for human-in-the-loop research tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from researchinfra.schemas import AgentBackendConfig, AgentTask


@dataclass(frozen=True)
class AgentBackendResult:
    """Result returned by an agent backend adapter."""

    task_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    message: str | None = None


class AgentBackend(ABC):
    """Base class for agent backends.

    Implementations may call local tools, external APIs, or manual workflows,
    but they should keep task records file-first and human approval explicit.
    """

    def __init__(self, config: AgentBackendConfig) -> None:
        self.config = config

    @property
    def backend_id(self) -> str:
        return self.config.id

    @abstractmethod
    def run(self, task: AgentTask, workspace: Path) -> AgentBackendResult:
        """Run or enqueue an agent task for a workspace."""
