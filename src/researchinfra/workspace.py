"""Workspace initialization for file-first ResearchInfra projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import yaml

from researchinfra.schemas import AgentBackendConfig, ModelProviderConfig, WorkspaceConfig


class WorkspaceError(RuntimeError):
    """Base exception for workspace operations."""


class WorkspaceExistsError(WorkspaceError):
    """Raised when refusing to initialize over a non-empty directory."""


WORKSPACE_DIRECTORIES: tuple[str, ...] = (
    ".researchinfra",
    "sources",
    "sources/papers",
    "sources/bib",
    "memory",
    "memory/claims",
    "memory/ideas",
    "memory/reviews",
    "projects",
    "experiments",
    "experiments/baselines",
    "runs",
    "figures",
    "drafts",
    "submissions",
    "skills",
    "skills/reading",
    "skills/ideation",
    "skills/experiment-planning",
    "skills/writing",
    "skills/reviewing",
    "skills/latex",
    "skills/submission",
    "agents",
    "agents/tasks",
    "agents/backends",
    "templates",
    "templates/venues",
    "templates/venues/acl",
    "templates/venues/neurips",
    "templates/venues/iclr",
    "templates/venues/icml",
    "templates/venues/arxiv",
    "docs",
)

SKILL_DESCRIPTIONS: dict[str, str] = {
    "reading": "Extract grounded notes from papers while preserving citations and uncertainty.",
    "ideation": "Develop and triage research ideas without inventing unsupported evidence.",
    "experiment-planning": "Turn claims and questions into executable experiment plans.",
    "writing": "Draft sections that link claims to papers, runs, figures, and tables.",
    "reviewing": "Review drafts, claims, and plans with human approval gates.",
    "latex": "Assist with LaTeX structure, references, tables, and venue constraints.",
    "submission": "Prepare checklists and packaging notes for venue submission workflows.",
}

VENUES: tuple[str, ...] = ("acl", "neurips", "iclr", "icml", "arxiv")


@dataclass(frozen=True)
class InitializedWorkspace:
    """Result returned by workspace initialization."""

    path: Path
    config_path: Path
    config: WorkspaceConfig


def default_workspace_config(name: str) -> WorkspaceConfig:
    """Build a default config with disabled provider and backend placeholders."""

    return WorkspaceConfig(
        name=name,
        description="A local, file-first ResearchInfra workspace.",
        directories={directory: directory for directory in WORKSPACE_DIRECTORIES},
        model_providers=[
            ModelProviderConfig(id="openai-compatible", provider="openai-compatible"),
            ModelProviderConfig(id="litellm", provider="litellm"),
            ModelProviderConfig(id="ollama", provider="ollama"),
            ModelProviderConfig(id="anthropic", provider="anthropic"),
            ModelProviderConfig(id="openrouter", provider="openrouter"),
            ModelProviderConfig(id="vllm", provider="vllm"),
        ],
        agent_backends=[
            AgentBackendConfig(id="manual", backend="manual", enabled=True),
            AgentBackendConfig(id="api", backend="api"),
            AgentBackendConfig(id="codex", backend="codex"),
            AgentBackendConfig(id="claude-code", backend="claude-code"),
            AgentBackendConfig(id="openhands", backend="openhands"),
            AgentBackendConfig(id="openclaw", backend="openclaw"),
        ],
    )


def init_workspace(
    path: str | Path, *, name: str | None = None, force: bool = False
) -> InitializedWorkspace:
    """Create a ResearchInfra workspace directory and starter files."""

    workspace_path = Path(path).expanduser().resolve()
    if workspace_path.exists() and any(workspace_path.iterdir()) and not force:
        raise WorkspaceExistsError(
            f"{workspace_path} already exists and is not empty. Use --force to add missing files."
        )

    workspace_name = name or workspace_path.name
    workspace_path.mkdir(parents=True, exist_ok=True)

    for directory in WORKSPACE_DIRECTORIES:
        (workspace_path / directory).mkdir(parents=True, exist_ok=True)

    config = default_workspace_config(workspace_name)
    config_path = workspace_path / ".researchinfra" / "workspace.yaml"
    _write_yaml(config_path, config.model_dump(mode="json"))
    _write_workspace_readme(workspace_path, workspace_name)
    _write_directory_guides(workspace_path)
    _write_skills(workspace_path)
    _write_venue_templates(workspace_path)
    _write_agent_placeholders(workspace_path)

    return InitializedWorkspace(path=workspace_path, config_path=config_path, config=config)


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_file(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def _write_workspace_readme(workspace_path: Path, workspace_name: str) -> None:
    _write_file(
        workspace_path / "README.md",
        f"""
        # {workspace_name}

        This is a ResearchInfra workspace: a local, file-first research operating
        system for papers, ideas, projects, experiments, runs, claims, drafts,
        submissions, skills, and agent tasks.

        Start with:

        - `sources/` for papers, BibTeX, and external references.
        - `memory/` for durable claims, ideas, reviews, and research notes.
        - `projects/` for scoped research efforts.
        - `experiments/` and `runs/` for planned experiments and execution records.
        - `drafts/` and `submissions/` for writing and venue preparation.
        - `agents/` and `skills/` for human-approved agent workflows.

        ResearchInfra does not create fake evidence. Link claims and drafts to
        real papers, experiments, figures, tables, and run records as they exist.
        """,
    )


def _write_directory_guides(workspace_path: Path) -> None:
    guides = {
        "sources/README.md": "Store papers, BibTeX files, PDFs, and source metadata here.",
        "memory/README.md": "Store durable ideas, claims, reviews, and research memory here.",
        "projects/README.md": "Create one directory per scoped research project.",
        "experiments/README.md": "Track planned experiments and baselines before runs.",
        "runs/README.md": "Store immutable run records, metrics, logs, and artifact pointers.",
        "figures/README.md": "Store figures and tables linked from claims, runs, and drafts.",
        "drafts/README.md": "Store outlines, Markdown drafts, LaTeX drafts, and evidence maps.",
        "submissions/README.md": "Store venue packaging checklists and submission artifacts.",
        "agents/README.md": "Store agent backend configs and task records with human approval.",
        "templates/README.md": "Store reusable project, experiment, draft, and venue templates.",
        "docs/README.md": "Store workspace-local documentation and lab conventions.",
    }
    for relative_path, text in guides.items():
        _write_file(workspace_path / relative_path, f"# {Path(relative_path).parent}\n\n{text}")


def _write_skills(workspace_path: Path) -> None:
    for skill, description in SKILL_DESCRIPTIONS.items():
        _write_file(
            workspace_path / "skills" / skill / "SKILL.md",
            f"""
            # {skill.replace("-", " ").title()}

            Purpose: {description}

            Scope:

            - Operate on local workspace files.
            - Preserve uncertainty and cite explicit evidence.
            - Ask for human review before changing research claims, results, or submissions.
            - Avoid fabricating papers, experiments, metrics, or conclusions.
            """,
        )


def _write_venue_templates(workspace_path: Path) -> None:
    for venue in VENUES:
        venue_name = venue.upper() if venue != "arxiv" else "arXiv"
        base = workspace_path / "templates" / "venues" / venue
        _write_file(
            base / "README.md",
            f"""
            # {venue_name} Template Placeholder

            Add the official {venue_name} style files and submission checklist here.
            Keep generated drafts linked to claims, papers, experiments, figures, tables,
            and run records.
            """,
        )
        _write_file(
            base / "main.tex",
            r"""
            \documentclass{article}
            \begin{document}
            % Replace this placeholder with the official venue template.
            \title{ResearchInfra Draft}
            \maketitle
            \end{document}
            """,
        )


def _write_agent_placeholders(workspace_path: Path) -> None:
    for backend in ("manual", "api", "codex", "claude-code", "openhands", "openclaw"):
        _write_yaml(
            workspace_path / "agents" / "backends" / f"{backend}.yaml",
            {
                "id": backend,
                "backend": backend,
                "enabled": backend == "manual",
                "human_approval_required": True,
                "notes": "Placeholder configuration. Add local commands or API routing when ready.",
            },
        )
