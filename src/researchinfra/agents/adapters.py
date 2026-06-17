"""Placeholder agent backend adapters.

These classes define stable extension points without binding ResearchInfra to a
single agent product or execution model.
"""

from __future__ import annotations

from pathlib import Path

from researchinfra.agents.base import AgentBackend, AgentBackendResult
from researchinfra.schemas import AgentTask


class PlaceholderAgentBackend(AgentBackend):
    """Adapter base for backends that are intentionally not implemented yet."""

    display_name = "placeholder"

    def run(self, task: AgentTask, workspace: Path) -> AgentBackendResult:
        return AgentBackendResult(
            task_id=task.id,
            status="needs_review",
            outputs={"workspace": str(workspace), "backend": self.config.backend},
            message=(
                f"{self.display_name} backend is configured as an extension point. "
                "Wire it to a real local command or API before automated execution."
            ),
        )


class ManualAgentBackend(PlaceholderAgentBackend):
    display_name = "Manual"


class ApiAgentBackend(PlaceholderAgentBackend):
    display_name = "API"


class CodexAgentBackend(PlaceholderAgentBackend):
    display_name = "Codex"


class ClaudeCodeAgentBackend(PlaceholderAgentBackend):
    display_name = "Claude Code"


class OpenHandsAgentBackend(PlaceholderAgentBackend):
    display_name = "OpenHands"


class OpenClawAgentBackend(PlaceholderAgentBackend):
    display_name = "OpenClaw"

