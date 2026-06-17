"""Agent backend interfaces and placeholder adapters."""

from researchinfra.agents.adapters import (
    ApiAgentBackend,
    ClaudeCodeAgentBackend,
    CodexAgentBackend,
    ManualAgentBackend,
    OpenClawAgentBackend,
    OpenHandsAgentBackend,
)
from researchinfra.agents.base import AgentBackend, AgentBackendResult

__all__ = [
    "AgentBackend",
    "AgentBackendResult",
    "ApiAgentBackend",
    "ClaudeCodeAgentBackend",
    "CodexAgentBackend",
    "ManualAgentBackend",
    "OpenClawAgentBackend",
    "OpenHandsAgentBackend",
]
