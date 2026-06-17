"""Typed schemas for the file-first ResearchInfra workspace."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ResearchInfraModel(BaseModel):
    """Base model with strict-ish defaults for durable file schemas."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


EvidenceKind = Literal[
    "paper",
    "experiment",
    "run",
    "figure",
    "table",
    "draft",
    "claim",
    "project",
]


class EvidenceLink(ResearchInfraModel):
    """A durable reference from one research object to supporting evidence."""

    kind: EvidenceKind
    ref: str = Field(..., min_length=1)
    note: str | None = None


class Paper(ResearchInfraModel):
    """A paper or scholarly source tracked by the workspace."""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=0)
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: HttpUrl | None = None
    bibtex_key: str | None = None
    path: str | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None
    notes: str | None = None


class Claim(ResearchInfraModel):
    """A research claim that can be grounded in explicit evidence."""

    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    status: Literal["hypothesis", "supported", "challenged", "retracted", "unknown"] = (
        "hypothesis"
    )
    evidence: list[EvidenceLink] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    owner: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Idea(ResearchInfraModel):
    """A research idea before it becomes a scoped project."""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    problem: str | None = None
    motivation: str | None = None
    related_papers: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    status: Literal["seed", "triaged", "active", "parked", "rejected"] = "seed"
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Project(ResearchInfraModel):
    """A scoped research project with linked ideas, claims, and artifacts."""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str | None = None
    status: Literal["planning", "active", "paused", "submitted", "archived"] = "planning"
    ideas: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    owner: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Experiment(ResearchInfraModel):
    """A planned or running experiment, separate from its concrete runs."""

    id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    question: str | None = None
    method: str | None = None
    baselines: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    status: Literal["planned", "ready", "running", "completed", "blocked", "abandoned"] = (
        "planned"
    )
    created_at: datetime = Field(default_factory=utc_now)


MetricValue = int | float | str | bool | None


class Run(ResearchInfraModel):
    """A concrete execution record for an experiment."""

    id: str = Field(..., min_length=1)
    experiment_id: str = Field(..., min_length=1)
    command: str | None = None
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    seed: int | None = None
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Draft(ResearchInfraModel):
    """A paper, report, or submission draft linked back to evidence."""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    project_id: str | None = None
    venue: str | None = None
    status: Literal["outline", "drafting", "internal_review", "submitted", "archived"] = (
        "outline"
    )
    sections: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)
    path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ReviewComment(ResearchInfraModel):
    """A structured review comment that can target a draft section or claim."""

    target: str | None = None
    severity: Literal["note", "minor", "major", "blocking"] = "note"
    text: str = Field(..., min_length=1)


class Review(ResearchInfraModel):
    """A human or agent review of a draft or research artifact."""

    id: str = Field(..., min_length=1)
    draft_id: str | None = None
    reviewer: str = Field(..., min_length=1)
    summary: str | None = None
    decision: Literal["accept", "revise", "reject", "no_decision"] = "no_decision"
    comments: list[ReviewComment] = Field(default_factory=list)
    checklist: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AgentTask(ResearchInfraModel):
    """A task record for a human-in-the-loop or automated agent backend."""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    backend: str = Field(..., min_length=1)
    prompt: str | None = None
    status: Literal["queued", "running", "needs_review", "completed", "failed", "cancelled"] = (
        "queued"
    )
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


ProviderKind = Literal[
    "openai-compatible",
    "litellm",
    "ollama",
    "anthropic",
    "openrouter",
    "vllm",
]


class ModelProviderConfig(ResearchInfraModel):
    """Configuration for a model provider without embedding credentials."""

    id: str = Field(..., min_length=1)
    provider: ProviderKind
    model: str | None = None
    base_url: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False


BackendKind = Literal["manual", "api", "codex", "claude-code", "openhands", "openclaw"]


class AgentBackendConfig(ResearchInfraModel):
    """Configuration for an agent backend adapter."""

    id: str = Field(..., min_length=1)
    backend: BackendKind
    model_provider_id: str | None = None
    command: list[str] = Field(default_factory=list)
    working_directory: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    enabled: bool = False


class WorkspaceConfig(ResearchInfraModel):
    """Top-level ResearchInfra workspace configuration."""

    schema_version: str = "0.1"
    name: str = Field(..., min_length=1)
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    directories: dict[str, str] = Field(default_factory=dict)
    model_providers: list[ModelProviderConfig] = Field(default_factory=list)
    agent_backends: list[AgentBackendConfig] = Field(default_factory=list)

