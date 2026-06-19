"""Workspace initialization for file-first ResearchInfra projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from researchinfra.schemas import AgentBackendConfig, ModelProviderConfig, WorkspaceConfig
from researchinfra.workspace_files import (
    WorkspaceDataError,
    read_yaml_mapping,
    validate_yaml_model,
    write_yaml,
)


class WorkspaceError(RuntimeError):
    """Base exception for workspace operations."""


class WorkspaceExistsError(WorkspaceError):
    """Raised when refusing to initialize over a non-empty directory."""


class WorkspaceNotInitializedError(WorkspaceError):
    """Raised when a command targets a directory without workspace metadata."""


class WorkspaceConfigError(WorkspaceError):
    """Raised when workspace metadata cannot be parsed or validated."""


WORKSPACE_DIRECTORIES: tuple[str, ...] = (
    ".researchinfra",
    "sources",
    "sources/papers",
    "sources/bib",
    "memory",
    "memory/documents",
    "memory/papers",
    "memory/readings",
    "memory/claims",
    "memory/ideas",
    "memory/reviews",
    "projects",
    "experiments",
    "experiments/baselines",
    "runs",
    "figures",
    "tables",
    "drafts",
    "submissions",
    "skills",
    "skills/reading",
    "skills/ideation",
    "skills/project-planning",
    "skills/experiment-planning",
    "skills/writing",
    "skills/reviewing",
    "skills/latex",
    "skills/submission",
    "skills/agents",
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
    "project-planning": "Turn papers, readings, and ideas into scoped project state.",
    "experiment-planning": "Turn claims and questions into executable experiment plans.",
    "writing": "Draft sections that link claims to papers, runs, figures, and tables.",
    "reviewing": "Review drafts, claims, and plans with human approval gates.",
    "latex": "Assist with LaTeX structure, references, tables, and venue constraints.",
    "submission": "Prepare checklists and packaging notes for venue submission workflows.",
    "agents": "Specify human-approved agent tasks without executing backends.",
}

VENUES: tuple[str, ...] = ("acl", "neurips", "iclr", "icml", "arxiv")


@dataclass(frozen=True)
class InitializedWorkspace:
    """Result returned by workspace initialization."""

    path: Path
    config_path: Path
    config: WorkspaceConfig
    config_written: bool


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
        model_defaults={},
        agent_backends=[
            AgentBackendConfig(id="manual", backend="manual", enabled=True),
            AgentBackendConfig(id="shell", backend="shell"),
            AgentBackendConfig(id="api", backend="api"),
            AgentBackendConfig(id="codex", backend="codex"),
            AgentBackendConfig(id="claude-code", backend="claude-code"),
            AgentBackendConfig(id="openhands", backend="openhands"),
            AgentBackendConfig(id="openclaw", backend="openclaw"),
        ],
    )


def init_workspace(
    path: str | Path,
    *,
    name: str | None = None,
    force: bool = False,
    reinitialize: bool = False,
    yes: bool = False,
) -> InitializedWorkspace:
    """Create a ResearchInfra workspace directory and starter files."""

    workspace_path = Path(path).expanduser().resolve()
    if force and reinitialize:
        raise WorkspaceError("Use either --force or --reinitialize, not both.")
    if reinitialize and not yes:
        raise WorkspaceError(
            "`--reinitialize` requires `--yes` because it overwrites generated "
            "configuration and starter files."
        )
    if workspace_path.exists() and not workspace_path.is_dir():
        raise WorkspaceError(f"Workspace path is not a directory: {workspace_path}")
    if workspace_path.exists() and any(workspace_path.iterdir()) and not (force or reinitialize):
        raise WorkspaceExistsError(
            f"{workspace_path} already exists and is not empty. Use --force to add missing "
            "files, or --reinitialize --yes to reset generated starter files."
        )

    workspace_name = (name or workspace_path.name).strip()
    if not workspace_name:
        raise WorkspaceError("Workspace name must not be empty.")
    config_path = workspace_path / ".researchinfra" / "workspace.yaml"
    config_exists = config_path.is_file()
    if config_exists and not reinitialize:
        config = load_workspace_config(workspace_path)
    else:
        config = default_workspace_config(workspace_name)

    workspace_path.mkdir(parents=True, exist_ok=True)

    for directory in WORKSPACE_DIRECTORIES:
        (workspace_path / directory).mkdir(parents=True, exist_ok=True)

    config_written = reinitialize or not config_exists
    if config_written:
        _write_yaml(config_path, config.model_dump(mode="json"), overwrite=True)
    _write_workspace_readme(workspace_path, config.name, overwrite=reinitialize)
    _write_directory_guides(workspace_path, overwrite=reinitialize)
    _write_skills(workspace_path, overwrite=reinitialize)
    _write_builtin_skill_files(workspace_path, overwrite=reinitialize)
    _write_venue_templates(workspace_path, overwrite=reinitialize)
    _write_agent_placeholders(workspace_path, overwrite=reinitialize)

    return InitializedWorkspace(
        path=workspace_path,
        config_path=config_path,
        config=config,
        config_written=config_written,
    )


def workspace_config_path(path: str | Path) -> Path:
    """Return the canonical workspace configuration path without creating files."""

    workspace = Path(path).expanduser().resolve()
    return workspace / ".researchinfra" / "workspace.yaml"


def load_workspace_config(path: str | Path) -> WorkspaceConfig:
    """Load and validate an initialized workspace configuration."""

    config_path = workspace_config_path(path)
    if not config_path.is_file():
        raise WorkspaceNotInitializedError(
            f"Workspace config not found: {config_path}. "
            "Run `researchinfra init <workspace>` first."
        )
    try:
        return validate_yaml_model(
            WorkspaceConfig, read_yaml_mapping(config_path), path=config_path
        )
    except WorkspaceDataError as exc:
        raise WorkspaceConfigError(str(exc)) from exc


def require_workspace(path: str | Path) -> Path:
    """Validate a workspace marker and return its normalized root path."""

    load_workspace_config(path)
    return Path(path).expanduser().resolve()


def _write_yaml(path: Path, data: object, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    write_yaml(path, data, create_parents=False)


def _write_file(path: Path, content: str, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        return
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def _write_workspace_readme(workspace_path: Path, workspace_name: str, *, overwrite: bool) -> None:
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
        overwrite=overwrite,
    )


def _write_directory_guides(workspace_path: Path, *, overwrite: bool) -> None:
    guides = {
        "sources/README.md": "Store papers, BibTeX files, PDFs, and source metadata here.",
        "memory/README.md": "Store Paper Cards, Idea Cards, claims, reviews, and notes here.",
        "projects/README.md": "Create one directory per scoped research project.",
        "experiments/README.md": "Track planned experiments and baselines before runs.",
        "runs/README.md": "Store immutable run records, metrics, logs, and artifact pointers.",
        "figures/README.md": "Store figures and tables linked from claims, runs, and drafts.",
        "tables/README.md": "Store table registries linked to explicit run records.",
        "drafts/README.md": "Store outlines, Markdown drafts, LaTeX drafts, and evidence maps.",
        "submissions/README.md": "Store venue packaging checklists and submission artifacts.",
        "agents/README.md": "Store agent backend configs and task records with human approval.",
        "templates/README.md": "Store reusable project, experiment, draft, and venue templates.",
        "docs/README.md": "Store workspace-local documentation and lab conventions.",
    }
    for relative_path, text in guides.items():
        _write_file(
            workspace_path / relative_path,
            f"# {Path(relative_path).parent}\n\n{text}",
            overwrite=overwrite,
        )


def _write_skills(workspace_path: Path, *, overwrite: bool) -> None:
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
            overwrite=overwrite,
        )


def _write_builtin_skill_files(workspace_path: Path, *, overwrite: bool) -> None:
    from researchinfra.skills import BUILTIN_SKILLS

    for skill in BUILTIN_SKILLS.values():
        base = workspace_path / "skills" / skill.category
        _write_yaml(
            base / f"{skill.name}.yaml",
            {
                "name": skill.name,
                "category": skill.category,
                "description": skill.description,
                "input_type": skill.input_type,
                "output_type": skill.output_type,
                "required_context": skill.required_context,
                "recommended_model": skill.recommended_model,
                "version": skill.version,
                "author": skill.author,
                "tags": skill.tags,
                "inputs": skill.inputs,
                "outputs": skill.outputs,
                "recommended_model_tier": skill.recommended_model_tier,
                "prompt_template": f"{skill.name}.md",
            },
            overwrite=overwrite,
        )
        _write_file(base / f"{skill.name}.md", skill.prompt_template, overwrite=overwrite)


def _write_venue_templates(workspace_path: Path, *, overwrite: bool) -> None:
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
            overwrite=overwrite,
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
            overwrite=overwrite,
        )


def _write_agent_placeholders(workspace_path: Path, *, overwrite: bool) -> None:
    for backend in ("manual", "shell", "api", "codex", "claude-code", "openhands", "openclaw"):
        _write_yaml(
            workspace_path / "agents" / "backends" / f"{backend}.yaml",
            {
                "id": backend,
                "backend": backend,
                "enabled": backend == "manual",
                "human_approval_required": True,
                "notes": "Placeholder configuration. Add local commands or API routing when ready.",
            },
            overwrite=overwrite,
        )
