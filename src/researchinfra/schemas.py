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


SourceType = Literal["paper", "blog", "repo", "note", "web", "unknown"]


class SourceLocalMetadata(ResearchInfraModel):
    """Metadata captured for a local file source."""

    path: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    extension: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    created_at: datetime | None = None


class SourceUrlMetadata(ResearchInfraModel):
    """Metadata captured for a URL source."""

    url: str = Field(..., min_length=1)
    domain: str | None = None


class Source(ResearchInfraModel):
    """A local or remote source tracked by a workspace registry."""

    id: str = Field(..., min_length=1)
    source_type: SourceType = "unknown"
    target: str = Field(..., min_length=1)
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    external_id: str | None = None
    pdf_url: str | None = None
    bibtex: str | None = None
    tags: list[str] = Field(default_factory=list)
    local: SourceLocalMetadata | None = None
    url: SourceUrlMetadata | None = None
    notes: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


FeedType = Literal["arxiv", "rss", "atom", "web"]


class Feed(ResearchInfraModel):
    """A configured source discovery feed."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: FeedType
    url: str | None = None
    query: str | None = None
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    last_synced_at: datetime | None = None


InboxStatus = Literal["new", "saved", "skipped"]


class InboxItem(ResearchInfraModel):
    """A discovered source candidate before promotion into the source registry."""

    id: str = Field(..., min_length=1)
    feed_id: str = Field(..., min_length=1)
    type: SourceType = "unknown"
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    external_id: str | None = None
    pdf_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: InboxStatus = "new"
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


ContentType = Literal["pdf", "markdown", "text", "html", "metadata", "unknown"]
ExtractionStatus = Literal["pending", "succeeded", "partial", "failed"]


class DocumentSection(ResearchInfraModel):
    """A coarse section in an extracted document."""

    name: str = Field(..., min_length=1)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)


class DocumentChunk(ResearchInfraModel):
    """A small inspectable chunk of extracted document text."""

    id: str = Field(..., min_length=1)
    section: str | None = None
    text: str = Field(..., min_length=1)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)


class EvidenceSpan(ResearchInfraModel):
    """A source-linked excerpt that can ground generated research text."""

    document_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    section: str | None = None
    chunk_id: str | None = None
    quote: str = Field(..., min_length=1)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)


class Document(ResearchInfraModel):
    """Extracted source content stored as local text and YAML metadata."""

    id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    title: str | None = None
    content_type: ContentType = "unknown"
    text_path: str = Field(..., min_length=1)
    metadata_path: str = Field(..., min_length=1)
    sections: list[DocumentSection] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    extraction_status: ExtractionStatus = "pending"
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Claim(ResearchInfraModel):
    """A research claim that can be grounded in explicit evidence."""

    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    status: Literal["hypothesis", "supported", "challenged", "retracted", "unknown"] = "hypothesis"
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
    thesis: str | None = None
    research_question: str | None = None
    motivation: str | None = None
    status: Literal["planning", "active", "paused", "submitted", "archived"] = "planning"
    ideas: list[str] = Field(default_factory=list)
    papers: list[str] = Field(default_factory=list)
    readings: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    target_venue: str | None = None
    owner: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


MetricValue = int | float | str | bool | None


class Baseline(ResearchInfraModel):
    """A baseline that an experiment plan should define before execution."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str | None = None
    implementation_status: Literal["proposed", "defined", "implemented", "verified"] = "proposed"
    evidence: list[EvidenceLink] = Field(default_factory=list)


class Ablation(ResearchInfraModel):
    """A planned ablation axis for an experiment matrix."""

    id: str = Field(..., min_length=1)
    factor: str = Field(..., min_length=1)
    levels: list[str] = Field(default_factory=list)
    hypothesis: str | None = None
    status: Literal["proposed", "ready", "run", "dropped"] = "proposed"


class ExperimentPlan(ResearchInfraModel):
    """A project-level experiment planning artifact."""

    id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    question: str | None = None
    hypothesis: str | None = None
    baselines: list[Baseline] = Field(default_factory=list)
    ablations: list[Ablation] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    status: Literal["draft", "ready", "running", "completed", "archived"] = "draft"
    created_at: datetime = Field(default_factory=utc_now)


class ResultRecord(ResearchInfraModel):
    """A file-first result or metric record for a concrete run."""

    id: str = Field(..., min_length=1)
    experiment_id: str = Field(..., min_length=1)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ClaimEvidenceLink(ResearchInfraModel):
    """A claim-to-evidence mapping used to gate drafts and results."""

    claim_id: str = Field(..., min_length=1)
    evidence: list[EvidenceLink] = Field(default_factory=list)
    status: Literal["missing", "partial", "supported", "contradicted"] = "missing"
    note: str | None = None


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
    status: Literal["planned", "ready", "running", "completed", "blocked", "abandoned"] = "planned"
    created_at: datetime = Field(default_factory=utc_now)


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
    status: Literal["outline", "drafting", "internal_review", "submitted", "archived"] = "outline"
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
    task_type: Literal["coding", "experiment", "writing", "review", "latex"] | None = None
    project_id: str | None = None
    backend: str = Field(..., min_length=1)
    suggested_backend: str | None = None
    context_files: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(default_factory=list)
    prompt: str | None = None
    status: Literal["queued", "running", "needs_review", "completed", "failed", "cancelled"] = (
        "queued"
    )
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class Skill(ResearchInfraModel):
    """A reusable research workflow prompt with metadata."""

    name: str = Field(..., min_length=1)
    category: str = "general"
    description: str = Field(..., min_length=1)
    input_type: str = "text"
    output_type: str = "markdown"
    required_context: list[str] = Field(default_factory=list)
    recommended_model: str = "optional"
    version: str = "0.1"
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    recommended_model_tier: str = "optional"
    prompt_template: str = Field(..., min_length=1)
    origin: Literal["built-in", "workspace"] = "built-in"


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
