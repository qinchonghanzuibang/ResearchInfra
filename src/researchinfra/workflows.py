"""End-to-end project, experiment, draft, and agent-task workflows."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import yaml

from researchinfra.schemas import AgentTask, Experiment, Project, Run, utc_now
from researchinfra.skills import SkillRunner


class WorkflowError(RuntimeError):
    """Base exception for project workflow operations."""


class ProjectNotFoundError(WorkflowError):
    """Raised when a project id or slug cannot be found."""


PROJECT_STATUSES = ("planning", "active", "paused", "submitted", "archived")
DRAFT_SECTIONS = ("intro", "related_work", "method", "experiments", "limitations")
TASK_TYPES = ("coding", "experiment", "writing", "review", "latex")
VENUES = ("acl", "iclr", "neurips", "icml", "arxiv")


class ProjectService:
    """Manage file-first ResearchInfra project directories."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects_dir = self.workspace / "projects"

    def create(
        self,
        *,
        name: str,
        from_idea: str | None = None,
        from_paper: str | None = None,
        from_reading: str | None = None,
    ) -> tuple[Project, Path]:
        """Create a project from optional existing research artifacts."""

        slug = _slug(name)
        project_id = f"project-{slug}"
        base = self.projects_dir / slug
        if (base / "project.yaml").exists():
            raise WorkflowError(f"Project already exists: {project_id}")

        for directory in ("context", "experiments", "draft", "agents/tasks", "reviews"):
            (base / directory).mkdir(parents=True, exist_ok=True)

        _require_seed_artifacts(
            workspace=self.workspace,
            idea_id=from_idea,
            paper_id=from_paper,
            reading_id=from_reading,
        )
        project = Project(
            id=project_id,
            title=name,
            thesis="To be refined by a human researcher.",
            research_question="What evidence-grounded question should this project answer?",
            motivation="Seeded from local ResearchInfra artifacts; requires human review.",
            ideas=[from_idea] if from_idea else [],
            papers=[from_paper] if from_paper else [],
            readings=[from_reading] if from_reading else [],
            open_questions=[
                "Which claims are supported by explicit papers, readings, or run records?",
                "Which baselines and datasets must be defined before experiments?",
            ],
            risks=[
                "Initial project state may be metadata-limited.",
                "No experimental results are claimed until run records exist.",
            ],
            next_actions=[
                "Review linked artifacts.",
                "Draft an experiment plan before running any experiments.",
                "Create agent tasks only with human-approved scope.",
            ],
            artifacts=_linked_artifacts(from_idea, from_paper, from_reading),
        )
        self._write(project)
        self._write_readme(project)
        self.write_context(project)
        return project, base

    def list(self) -> list[Project]:
        """Return all projects sorted by creation time."""

        projects: list[Project] = []
        if not self.projects_dir.exists():
            return []
        for path in sorted(self.projects_dir.glob("*/project.yaml")):
            projects.append(Project.model_validate(_read_yaml(path)))
        return sorted(projects, key=lambda project: project.created_at)

    def get(self, project_id: str) -> Project:
        """Return a project by id or slug."""

        direct = self.projects_dir / project_id / "project.yaml"
        if direct.exists():
            return Project.model_validate(_read_yaml(direct))
        for project in self.list():
            if project.id == project_id or _slug(project.title) == project_id:
                return project
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    def path_for(self, project: Project | str) -> Path:
        """Return the project directory."""

        item = self.get(project) if isinstance(project, str) else project
        return self.projects_dir / item.id.removeprefix("project-")

    def add_paper(self, project_id: str, paper_id: str) -> Project:
        """Link a Paper Card to a project."""

        self._require_file(self.workspace / "memory" / "papers" / f"{paper_id}.yaml", "Paper")
        project = self.get(project_id)
        return self._append_link(project, "papers", paper_id, f"paper:{paper_id}")

    def add_reading(self, project_id: str, reading_id: str) -> Project:
        """Link a reading artifact to a project."""

        self._require_reading(reading_id)
        project = self.get(project_id)
        return self._append_link(project, "readings", reading_id, f"reading:{reading_id}")

    def status(self, project_id: str) -> str:
        """Render a compact project status summary."""

        project = self.get(project_id)
        base = self.path_for(project)
        run_registry = _read_yaml(base / "experiments" / "run_registry.yaml")
        runs = run_registry.get("runs", []) if isinstance(run_registry, dict) else []
        return dedent(
            f"""
            Project: {project.id}
            Status: {project.status}
            Papers: {len(project.papers)}
            Readings: {len(project.readings)}
            Ideas: {len(project.ideas)}
            Experiments: {len(project.experiments)}
            Runs: {len(runs)}
            Next actions:
            {_template_bullet_list(project.next_actions)}
            Risks:
            {_template_bullet_list(project.risks)}
            """
        ).strip()

    def write_context(self, project: Project) -> Path:
        """Write an up-to-date Markdown context file for skills."""

        base = self.path_for(project)
        context_path = base / "context" / "project_context.md"
        content = dedent(
            f"""
            # Project Context: {project.title}

            - Project ID: `{project.id}`
            - Status: `{project.status}`
            - Target venue: `{project.target_venue or "not set"}`

            ## Thesis

            {project.thesis or "Not set."}

            ## Research Question

            {project.research_question or "Not set."}

            ## Motivation

            {project.motivation or "Not set."}

            ## Linked Artifacts

            - Ideas: {", ".join(project.ideas) if project.ideas else "none"}
            - Papers: {", ".join(project.papers) if project.papers else "none"}
            - Readings: {", ".join(project.readings) if project.readings else "none"}

            ## Open Questions

            {_template_bullet_list(project.open_questions)}

            ## Decisions

            {_template_bullet_list(project.decisions)}

            ## Risks

            {_template_bullet_list(project.risks)}

            ## Next Actions

            {_template_bullet_list(project.next_actions)}

            ## Evidence Rules

            Do not claim experimental results unless they are linked to run records.
            Cite Paper Cards, reading notes, document chunks, figures, tables, or run records
            for claims. Mark missing content and missing experiments explicitly.
            """
        ).strip()
        context_path.write_text(content + "\n", encoding="utf-8")
        _write_yaml(
            base / "context" / "links.yaml",
            {
                "project_id": project.id,
                "ideas": project.ideas,
                "papers": project.papers,
                "readings": project.readings,
                "artifacts": project.artifacts,
                "updated_at": utc_now().isoformat(),
            },
        )
        return context_path

    def _append_link(self, project: Project, field: str, item_id: str, artifact: str) -> Project:
        values = list(getattr(project, field))
        if item_id not in values:
            values.append(item_id)
        artifacts = list(project.artifacts)
        if artifact not in artifacts:
            artifacts.append(artifact)
        updated = project.model_copy(
            update={field: values, "artifacts": artifacts, "updated_at": utc_now()}
        )
        self._write(updated)
        self.write_context(updated)
        return updated

    def _write(self, project: Project) -> None:
        base = self.path_for(project)
        base.mkdir(parents=True, exist_ok=True)
        _write_yaml(base / "project.yaml", project.model_dump(mode="json"))

    def _write_readme(self, project: Project) -> None:
        readme = self.path_for(project) / "README.md"
        readme.write_text(
            dedent(
                f"""
                # {project.title}

                This ResearchInfra project is file-first and evidence-gated.

                - `project.yaml` stores project state.
                - `context/` stores linked artifact context for skills and agents.
                - `experiments/` stores plans, registries, run records, and claim evidence.
                - `draft/` stores outlines and section drafts.
                - `agents/tasks/` stores human-approved task specs.
                - `reviews/` stores review notes and checklists.

                No results are claimed until linked to run records.
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def _require_file(self, path: Path, label: str) -> None:
        if not path.exists():
            raise WorkflowError(f"{label} artifact not found: {path}")

    def _require_reading(self, reading_id: str) -> None:
        path = self.workspace / "memory" / "readings" / reading_id / "metadata.yaml"
        if not path.exists():
            raise WorkflowError(f"Reading artifact not found: {reading_id}")


class ExperimentService:
    """Create experiment planning scaffolds and run records."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)
        self.runner = SkillRunner(self.workspace)

    def render_plan_prompt(self, project_id: str) -> str:
        """Render the experiment planning prompt for a project."""

        project = self.projects.get(project_id)
        context_path = self.projects.write_context(project)
        return self.runner.render(
            "experiment_plan",
            str(context_path),
            output_schema=(
                "Markdown experiment plan with proposed baselines, ablations, metrics, "
                "missing evidence, and explicit no-results warnings."
            ),
        )

    def plan(self, project_id: str) -> tuple[Path, Path, Path, Path, Path]:
        """Write experiment planning artifacts for a project."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project) / "experiments"
        base.mkdir(parents=True, exist_ok=True)
        experiment_id = f"experiment-{project.id.removeprefix('project-')}-001"
        experiment = Experiment(
            id=experiment_id,
            project_id=project.id,
            title=f"{project.title} initial experiment plan",
            question=project.research_question,
            expected_artifacts=[
                "baseline_registry.yaml",
                "ablation_matrix.yaml",
                "run_registry.yaml",
                "claim_evidence.yaml",
            ],
        )
        if experiment.id not in project.experiments:
            updated = project.model_copy(
                update={
                    "experiments": [*project.experiments, experiment.id],
                    "updated_at": utc_now(),
                }
            )
            self.projects._write(updated)
            self.projects.write_context(updated)

        plan_path = base / "experiment_plan.md"
        baseline_path = base / "baseline_registry.yaml"
        ablation_path = base / "ablation_matrix.yaml"
        run_path = base / "run_registry.yaml"
        claim_path = base / "claim_evidence.yaml"
        plan_path.write_text(
            _experiment_plan_markdown(project, experiment) + "\n",
            encoding="utf-8",
        )
        _write_yaml(
            baseline_path,
            {
                "project_id": project.id,
                "experiment_id": experiment.id,
                "baselines": [],
                "warnings": [
                    "Baselines are not defined yet.",
                    "Do not compare against missing baselines.",
                ],
            },
        )
        _write_yaml(
            ablation_path,
            {
                "project_id": project.id,
                "experiment_id": experiment.id,
                "ablations": [],
                "warnings": ["Ablations are proposals until implemented and run."],
            },
        )
        _write_yaml(
            run_path,
            {
                "project_id": project.id,
                "experiment_id": experiment.id,
                "runs": [],
                "warnings": ["No runs have been recorded; no results are supported."],
            },
        )
        _write_yaml(
            claim_path,
            {
                "project_id": project.id,
                "claims": [],
                "warnings": ["Claims remain unsupported until linked to evidence."],
            },
        )
        return plan_path, baseline_path, ablation_path, run_path, claim_path

    def list(self, project_id: str) -> list[str]:
        """List planned experiment ids for a project."""

        return self.projects.get(project_id).experiments

    def add_run(
        self,
        *,
        project_id: str,
        experiment_id: str,
        metrics: dict[str, object],
    ) -> tuple[Run, Path]:
        """Append a run record with explicit user-provided metrics."""

        project = self.projects.get(project_id)
        if experiment_id not in project.experiments:
            raise WorkflowError(f"Experiment not found in project: {experiment_id}")
        base = self.projects.path_for(project) / "experiments"
        run_path = base / "run_registry.yaml"
        data = _read_yaml(run_path)
        runs = list(data.get("runs", [])) if isinstance(data, dict) else []
        run = Run(
            id=f"run-{len(runs) + 1:04d}",
            experiment_id=experiment_id,
            status="completed",
            metrics=metrics,
            notes="User-provided metric record. Verify artifacts before using in claims.",
            finished_at=utc_now(),
        )
        runs.append(run.model_dump(mode="json"))
        _write_yaml(
            run_path,
            {
                "project_id": project.id,
                "experiment_id": experiment_id,
                "runs": runs,
                "warnings": ["Only user-provided metrics are recorded here."],
            },
        )
        return run, run_path


class DraftService:
    """Create draft outlines and section scaffolds."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)
        self.runner = SkillRunner(self.workspace)

    def render_outline_prompt(self, project_id: str, *, venue: str | None = None) -> str:
        """Render a draft outline prompt."""

        project = self.projects.get(project_id)
        context_path = self.projects.write_context(project)
        return self.runner.render(
            "draft_outline",
            str(context_path),
            output_schema=f"Venue-aware outline for {venue or 'unspecified venue'}.",
        )

    def outline(self, project_id: str, *, venue: str | None = None) -> Path:
        """Write a draft outline scaffold."""

        if venue is not None and venue not in VENUES:
            raise WorkflowError(f"Unsupported venue: {venue}")
        project = self.projects.get(project_id)
        draft_dir = self.projects.path_for(project) / "draft"
        draft_dir.mkdir(parents=True, exist_ok=True)
        path = draft_dir / "outline.md"
        path.write_text(_draft_outline_markdown(project, venue=venue) + "\n", encoding="utf-8")
        return path

    def render_section_prompt(self, project_id: str, *, section: str) -> str:
        """Render a draft section prompt."""

        _validate_section(section)
        project = self.projects.get(project_id)
        context_path = self.projects.write_context(project)
        return self.runner.render(
            "draft_section",
            str(context_path),
            output_schema=f"Evidence-gated `{section}` section draft scaffold.",
        )

    def section(self, project_id: str, *, section: str) -> Path:
        """Write a draft section scaffold."""

        _validate_section(section)
        project = self.projects.get(project_id)
        draft_dir = self.projects.path_for(project) / "draft"
        draft_dir.mkdir(parents=True, exist_ok=True)
        path = draft_dir / f"{section}.md"
        path.write_text(_draft_section_markdown(project, section=section) + "\n", encoding="utf-8")
        return path


class AgentTaskService:
    """Create and inspect project-local agent task specs."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)

    def create(self, *, project_id: str, task_type: str, title: str) -> tuple[AgentTask, Path]:
        """Create a task spec without executing any backend."""

        if task_type not in TASK_TYPES:
            raise WorkflowError(f"Unsupported task type: {task_type}")
        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        tasks_dir = base / "agents" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(tasks_dir.glob("task-*.yaml"))
        task = AgentTask(
            id=f"task-{task_type}-{len(existing) + 1:04d}",
            title=title,
            task_type=task_type,  # type: ignore[arg-type]
            project_id=project.id,
            backend="manual",
            suggested_backend=_suggested_backend(task_type),
            context_files=_task_context_files(base),
            expected_outputs=_expected_outputs(task_type),
            constraints=[
                "Do not fabricate papers, citations, experiments, metrics, or results.",
                "Ask for human review before changing claims or submission artifacts.",
                "Record outputs as local files and link them back to project evidence.",
            ],
            verification_commands=_verification_commands(task_type),
            prompt=(
                f"Prepare a {task_type} task for `{project.title}`. "
                "Use only the listed context files and preserve human approval gates."
            ),
        )
        path = tasks_dir / f"{task.id}.yaml"
        _write_yaml(path, task.model_dump(mode="json"))
        return task, path

    def list(self, project_id: str) -> list[AgentTask]:
        """List project task specs."""

        project = self.projects.get(project_id)
        tasks_dir = self.projects.path_for(project) / "agents" / "tasks"
        tasks = []
        for path in sorted(tasks_dir.glob("*.yaml")):
            tasks.append(AgentTask.model_validate(_read_yaml(path)))
        return tasks

    def get(self, *, project_id: str, task_id: str) -> AgentTask:
        """Return a task spec."""

        project = self.projects.get(project_id)
        path = self.projects.path_for(project) / "agents" / "tasks" / f"{task_id}.yaml"
        if not path.exists():
            raise WorkflowError(f"Agent task not found: {task_id}")
        return AgentTask.model_validate(_read_yaml(path))


def _experiment_plan_markdown(project: Project, experiment: Experiment) -> str:
    return dedent(
        f"""
        # Experiment Plan: {project.title}

        > WARNING: This is a planning scaffold. No experiment has been run and no
        > result is claimed until a run record is added to `run_registry.yaml`.

        ## Experiment

        - Experiment ID: `{experiment.id}`
        - Project ID: `{project.id}`
        - Status: `{experiment.status}`

        ## Research Question

        {project.research_question or "Define before running experiments."}

        ## Baselines To Define

        No baselines are defined yet. Add justified baselines before comparing methods.

        ## Ablations To Define

        No ablations are defined yet. Add ablation factors only when implementation details exist.

        ## Metrics To Justify

        No metrics are justified yet. Add metrics with their failure modes and artifacts.

        ## Missing Evidence

        - Link datasets, baselines, and evaluation protocols.
        - Link run records before using results in claims or drafts.
        """
    ).strip()


def _draft_outline_markdown(project: Project, *, venue: str | None) -> str:
    return dedent(
        f"""
        # Draft Outline: {project.title}

        > WARNING: This outline is evidence-gated. Do not claim results unless they are
        > linked to run records in `projects/{project.id.removeprefix("project-")}/experiments/`.

        - Venue: `{venue or "not set"}`
        - Project ID: `{project.id}`

        ## Introduction

        State the problem and motivation. Mark unsupported claims as TODO.

        ## Related Work

        Cite linked Paper Cards and reading notes. Do not invent citations.

        ## Method

        Describe only planned or implemented methods. Mark speculative ideas clearly.

        ## Experiments

        Missing experiment warning: no result should appear here without a run record.

        ## Limitations

        Record missing evidence, failed assumptions, and project risks.
        """
    ).strip()


def _draft_section_markdown(project: Project, *, section: str) -> str:
    return dedent(
        f"""
        # {section.replace("_", " ").title()}: {project.title}

        > WARNING: Draft section scaffold. Link every claim to evidence and do not claim
        > experimental results unless backed by a run record.

        ## Evidence Available

        - Papers: {", ".join(project.papers) if project.papers else "none"}
        - Readings: {", ".join(project.readings) if project.readings else "none"}

        ## Missing Evidence

        - Add citations, document chunks, figures, tables, or run records before finalizing.

        ## Draft Notes

        Write the `{section}` section here after reviewing evidence.
        """
    ).strip()


def _require_seed_artifacts(
    *,
    workspace: Path,
    idea_id: str | None,
    paper_id: str | None,
    reading_id: str | None,
) -> None:
    if idea_id and not (workspace / "memory" / "ideas" / f"{idea_id}.yaml").exists():
        raise WorkflowError(f"Idea Card not found: {idea_id}")
    if paper_id and not (workspace / "memory" / "papers" / f"{paper_id}.yaml").exists():
        raise WorkflowError(f"Paper Card not found: {paper_id}")
    if (
        reading_id
        and not (workspace / "memory" / "readings" / reading_id / "metadata.yaml").exists()
    ):
        raise WorkflowError(f"Reading artifact not found: {reading_id}")


def _linked_artifacts(
    idea_id: str | None,
    paper_id: str | None,
    reading_id: str | None,
) -> list[str]:
    artifacts = []
    if idea_id:
        artifacts.append(f"idea:{idea_id}")
    if paper_id:
        artifacts.append(f"paper:{paper_id}")
    if reading_id:
        artifacts.append(f"reading:{reading_id}")
    return artifacts


def _task_context_files(base: Path) -> list[str]:
    candidates = [
        base / "project.yaml",
        base / "context" / "project_context.md",
        base / "experiments" / "experiment_plan.md",
        base / "experiments" / "run_registry.yaml",
        base / "draft" / "outline.md",
    ]
    return [str(path.relative_to(base.parent.parent)) for path in candidates if path.exists()]


def _expected_outputs(task_type: str) -> list[str]:
    return {
        "coding": ["Patch or implementation notes", "Verification command output"],
        "experiment": ["Updated experiment plan or run record", "Artifact links"],
        "writing": ["Draft section or outline changes", "Evidence links"],
        "review": ["Review comments", "Blocking issues and missing evidence"],
        "latex": ["LaTeX edits or checklist", "Compilation or formatting notes"],
    }[task_type]


def _verification_commands(task_type: str) -> list[str]:
    if task_type == "coding":
        return ["python -m pytest", "python -m ruff check ."]
    if task_type == "latex":
        return ["latexmk -pdf main.tex # when venue files are present"]
    return ["researchinfra project status <project-id> --workspace <workspace>"]


def _suggested_backend(task_type: str) -> str:
    return "codex" if task_type in {"coding", "latex"} else "manual"


def _validate_section(section: str) -> None:
    if section not in DRAFT_SECTIONS:
        raise WorkflowError(f"Unsupported draft section: {section}")


def _bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none"


def _template_bullet_list(values: list[str]) -> str:
    return _bullet_list(values).replace("\n", "\n            ")


def _read_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WorkflowError(f"Invalid YAML object: {path}")
    return data


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "untitled"
