"""Reusable skill loading and prompt rendering."""

from __future__ import annotations

from pathlib import Path
from string import Template
from textwrap import dedent
from typing import Any

import yaml

from researchinfra.documents import DocumentStore, evidence_prompt_context
from researchinfra.schemas import Document, Skill, Source
from researchinfra.sources import SourceNotFoundError, SourceRegistry


class SkillError(RuntimeError):
    """Base exception for skill operations."""


class SkillNotFoundError(SkillError):
    """Raised when a skill cannot be found."""


READING_MODES: tuple[str, ...] = (
    "skim",
    "deep",
    "idea",
    "reviewer",
    "reproduce",
    "related_work",
)


BUILTIN_SKILLS: dict[str, Skill] = {
    "project_brain": Skill(
        name="project_brain",
        category="project-planning",
        description="Turn papers, readings, and ideas into a cautious project brain.",
        input_type="artifact_context",
        output_type="project_brain_markdown",
        required_context=["metadata", "warnings", "input_text"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["project", "planning"],
        inputs=["idea_card", "paper_card", "reading", "manual_context"],
        outputs=["project_yaml", "project_readme", "project_context"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Build a ResearchInfra project brain from the provided context.

            Context:
            $input_text

            Output schema:
            $output_schema

            Include:
            - Thesis
            - Research question
            - Motivation
            - Linked papers, readings, and ideas
            - Claims that are only hypotheses unless evidence is explicit
            - Open questions
            - Decisions
            - Risks
            - Next actions
            - Target venue if known

            Constraints:
            - Do not fabricate paper content, citations, experiments, metrics, or results.
            - Mark missing or partial context clearly.
            - Keep human review requirements explicit.
            """
        ).strip(),
    ),
    "paper_card": Skill(
        name="paper_card",
        category="writing",
        description=(
            "Create an evidence-aware Paper Card from source metadata and optional content."
        ),
        input_type="source",
        output_type="paper_card_markdown",
        required_context=[
            "source",
            "metadata",
            "chunks",
            "evidence_instructions",
            "warnings",
        ],
        recommended_model="standard",
        version="0.2",
        author="ResearchInfra",
        tags=["paper", "evidence"],
        inputs=["source"],
        outputs=["paper_card_markdown", "paper_metadata_yaml"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            You are helping create a ResearchInfra Paper Card.

            Profile:
            $profile

            Source:
            $source

            Metadata:
            $metadata

            Document:
            $document

            Chunks:
            $chunks

            Evidence instructions:
            $evidence_instructions

            Warnings:
            $warnings

            Output schema:
            $output_schema

            Important constraints:
            - Do not fabricate paper content, citations, experiments, datasets, metrics, or results.
            - Cite explicit evidence spans using document_id and chunk_id when chunks are present.
            - If content is missing or partial, include that limitation.
            - Keep claims separate from hypotheses.
            """
        ).strip(),
    ),
    "idea_card": Skill(
        name="idea_card",
        category="ideation",
        description="Generate a cautious Idea Card from a Paper Card or source context.",
        input_type="paper_card",
        output_type="idea_card_markdown",
        required_context=["metadata", "warnings"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["idea", "hypothesis"],
        inputs=["paper_card"],
        outputs=["idea_card_markdown", "idea_metadata_yaml"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            You are helping create a ResearchInfra Idea Card.

            Input context:
            $input_text

            Output schema:
            $output_schema

            Important constraints:
            - Do not invent results, citations, or experiments as completed work.
            - Mark all proposed experiments as proposals, not evidence.
            - Explicitly warn when the idea is based only on limited metadata.
            """
        ).strip(),
    ),
    "claim_check": Skill(
        name="claim_check",
        category="reviewing",
        description="Check whether a claim is supported by available workspace evidence.",
        input_type="claim_or_note",
        output_type="claim_review",
        required_context=["metadata", "chunks", "evidence_instructions"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["claim", "review"],
        inputs=["claim_or_note"],
        outputs=["claim_review"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Review the following claim or note against available context:

            $input_text

            Evidence context:
            $chunks

            Return:
            - Claim being checked
            - Evidence present
            - Evidence missing
            - Unsupported leaps
            - Recommended human follow-up

            Do not add new claims or cite sources that are not present in the input.
            """
        ).strip(),
    ),
    "experiment_plan": Skill(
        name="experiment_plan",
        category="experiment-planning",
        description="Draft an evidence-gated experiment plan from project context.",
        input_type="project_context",
        output_type="experiment_plan",
        required_context=["input_text", "warnings", "output_schema"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["experiment", "planning"],
        inputs=["idea_or_claim"],
        outputs=["experiment_plan"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Draft a ResearchInfra experiment plan from this project context:

            $input_text

            Output schema:
            $output_schema

            Include:
            - Question
            - Hypothesis
            - Required datasets or sources
            - Baselines to define before running
            - Metrics to justify
            - Artifacts to record
            - Risks, confounders, and missing evidence

            Do not present any proposed experiment as already run.
            Do not invent datasets, baselines, metrics, or results.
            """
        ).strip(),
    ),
    "draft_outline": Skill(
        name="draft_outline",
        category="writing",
        description="Create an evidence-gated draft outline from project context.",
        input_type="project_context",
        output_type="draft_outline_markdown",
        required_context=["input_text", "warnings", "output_schema"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["draft", "outline"],
        inputs=["project_context"],
        outputs=["draft_outline_markdown"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Create a ResearchInfra draft outline from this project context:

            $input_text

            Output schema:
            $output_schema

            Required warnings:
            - Mark missing experiments explicitly.
            - Do not claim results unless linked to run records.
            - Do not invent citations or related work.
            - Link every claim to evidence or mark it as a hypothesis.
            """
        ).strip(),
    ),
    "draft_section": Skill(
        name="draft_section",
        category="writing",
        description="Draft a single evidence-gated paper section from project context.",
        input_type="project_context",
        output_type="draft_section_markdown",
        required_context=["input_text", "warnings", "output_schema"],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["draft", "section"],
        inputs=["project_context"],
        outputs=["draft_section_markdown"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Draft a ResearchInfra paper section from this project context:

            $input_text

            Output schema:
            $output_schema

            Constraints:
            - Include evidence warnings and missing-experiment warnings.
            - Do not claim results unless linked to run records.
            - Do not invent citations, comparisons, metrics, or datasets.
            - Prefer TODO markers over unsupported prose.
            """
        ).strip(),
    ),
    "agent_task": Skill(
        name="agent_task",
        category="agents",
        description="Create a human-approved agent task spec from project context.",
        input_type="project_context",
        output_type="agent_task_yaml",
        required_context=["input_text", "warnings", "output_schema"],
        recommended_model="optional",
        version="0.1",
        author="ResearchInfra",
        tags=["agent", "task"],
        inputs=["project_context"],
        outputs=["agent_task_yaml"],
        recommended_model_tier="optional",
        prompt_template=dedent(
            """
            Create a ResearchInfra agent task spec from this project context:

            $input_text

            Output schema:
            $output_schema

            The task spec must include:
            - Context files
            - Expected outputs
            - Constraints
            - Verification commands
            - Suggested backend

            Do not execute any backend. Do not invent completed work.
            """
        ).strip(),
    ),
}


def _reading_skill(
    *,
    name: str,
    description: str,
    output_schema: str,
    focus: str,
) -> Skill:
    return Skill(
        name=name,
        category="reading",
        description=description,
        input_type="source_or_document",
        output_type="reading_notes_markdown",
        required_context=[
            "source",
            "document",
            "metadata",
            "chunks",
            "evidence_instructions",
            "warnings",
        ],
        recommended_model="standard",
        version="0.1",
        author="ResearchInfra",
        tags=["reading", name.removeprefix("read_")],
        inputs=["source_or_document"],
        outputs=["reading_notes_markdown"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            f"""
            You are reading a research paper with the `{name.removeprefix("read_")}` mode.

            Profile:
            $profile

            Source:
            $source

            Document:
            $document

            Metadata:
            $metadata

            Chunks:
            $chunks

            Evidence instructions:
            $evidence_instructions

            Warnings:
            $warnings

            Reading focus:
            {focus}

            Output schema:
            {output_schema}

            Constraints:
            - Do not fabricate paper content, citations, experiments, datasets, metrics, or results.
            - Cite document chunks when making paper-specific observations.
            - If content is missing or partial, say so explicitly.
            - Separate evidence-backed observations from hypotheses or ideas.
            """
        ).strip(),
    )


BUILTIN_SKILLS.update(
    {
        "read_skim": _reading_skill(
            name="read_skim",
            description="Quick triage and whether to read a paper deeply.",
            focus="Decide whether this source deserves deeper reading and why.",
            output_schema=(
                "- Triage decision\n- Why it matters\n- Key evidence spans\n"
                "- Missing context\n- Next action"
            ),
        ),
        "read_deep": _reading_skill(
            name="read_deep",
            description="Structured section-level understanding.",
            focus="Build a careful section-level understanding grounded in extracted chunks.",
            output_schema=(
                "- Problem\n- Method\n- Evidence\n- Assumptions\n- Limitations\n- Questions"
            ),
        ),
        "read_idea": _reading_skill(
            name="read_idea",
            description="Limitations, gaps, and possible research ideas.",
            focus="Identify limitations and research gaps without presenting ideas as evidence.",
            output_schema=(
                "- Gaps\n- Possible ideas\n- Evidence needed\n- Risks\n- Human review checklist"
            ),
        ),
        "read_reviewer": _reading_skill(
            name="read_reviewer",
            description="Novelty, weakness, missing experiments, and overclaims.",
            focus="Read like a critical reviewer while avoiding unsupported accusations.",
            output_schema=(
                "- Summary\n- Strengths\n- Weaknesses\n- Missing experiments\n"
                "- Overclaims\n- Questions"
            ),
        ),
        "read_reproduce": _reading_skill(
            name="read_reproduce",
            description="Datasets, models, training, evaluation, and implementation risks.",
            focus="Extract reproducibility-relevant details and what is missing.",
            output_schema=(
                "- Artifacts needed\n- Datasets\n- Models\n- Training\n- Evaluation\n- Risks"
            ),
        ),
        "read_related_work": _reading_skill(
            name="read_related_work",
            description="Concise related-work summary with citation-ready notes.",
            focus="Summarize how this work relates to a research area with citation-ready notes.",
            output_schema=(
                "- Citation-ready summary\n- Contribution\n- Compared work\n"
                "- Useful quote spans\n- Caveats"
            ),
        ),
    }
)


class SkillRunner:
    """Load skills and render prompts from workspace inputs."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry = SourceRegistry(self.workspace)
        self.documents = DocumentStore(self.workspace)

    def list(self, *, category: str | None = None) -> list[Skill]:
        """Return built-in and workspace skills."""

        skills = {name: skill for name, skill in BUILTIN_SKILLS.items()}
        for skill in self._workspace_skills():
            skills[skill.name] = skill
        values = sorted(skills.values(), key=lambda skill: (skill.category, skill.name))
        if category is not None:
            values = [skill for skill in values if skill.category == category]
        return values

    def get(self, name: str) -> Skill:
        """Return a skill by name."""

        for skill in self.list():
            if skill.name == name:
                return skill
        raise SkillNotFoundError(f"Skill not found: {name}")

    def create(self, name: str, *, category: str) -> tuple[Path, Path]:
        """Create a workspace skill skeleton."""

        category_dir = self.workspace / "skills" / category
        category_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = category_dir / f"{name}.yaml"
        prompt_path = category_dir / f"{name}.md"
        if yaml_path.exists() or prompt_path.exists():
            raise SkillError(f"Skill already exists: {name}")
        prompt_template = dedent(
            """
            # $profile

            Source:
            $source

            Document:
            $document

            Metadata:
            $metadata

            Chunks:
            $chunks

            Evidence instructions:
            $evidence_instructions

            Warnings:
            $warnings

            Output schema:
            $output_schema
            """
        ).strip()
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "name": name,
                    "category": category,
                    "description": "Describe what this skill should do.",
                    "input_type": "source_or_document",
                    "output_type": "markdown",
                    "required_context": ["source", "document", "chunks", "warnings"],
                    "prompt_template": f"{name}.md",
                    "recommended_model": "optional",
                    "version": "0.1",
                    "author": None,
                    "tags": [],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        prompt_path.write_text(prompt_template + "\n", encoding="utf-8")
        return yaml_path, prompt_path

    def render(
        self,
        name: str,
        input_value: str,
        *,
        profile: str = "ResearchInfra cautious research assistant",
        output_schema: str | None = None,
        include_document: bool = True,
    ) -> str:
        """Render a skill prompt for a file path, source id, or document id."""

        skill = self.get(name)
        context = self.context_for_input(
            input_value,
            profile=profile,
            output_schema=output_schema or _default_output_schema(skill),
            include_document=include_document,
        )
        return Template(skill.prompt_template).safe_substitute(context)

    def context_for_input(
        self,
        input_value: str,
        *,
        profile: str = "ResearchInfra cautious research assistant",
        output_schema: str = "Markdown notes with explicit evidence references.",
        include_document: bool = True,
    ) -> dict[str, str]:
        """Build prompt variables for a file path, source id, or document id."""

        if include_document:
            try:
                document = self.documents.get(input_value)
            except Exception:
                document = None
            if document is not None:
                source = _try_get_source(self.registry, document.source_id)
                return self._context(
                    source=source,
                    document=document,
                    input_value=input_value,
                    profile=profile,
                    output_schema=output_schema,
                )

        try:
            source = self.registry.get(input_value)
        except SourceNotFoundError:
            return self._file_context(input_value, profile=profile, output_schema=output_schema)
        document = self.documents.find_by_source_id(source.id) if include_document else None
        return self._context(
            source=source,
            document=document,
            input_value=input_value,
            profile=profile,
            output_schema=output_schema,
        )

    def _context(
        self,
        *,
        source: Source | None,
        document: Document | None,
        input_value: str,
        profile: str,
        output_schema: str,
    ) -> dict[str, str]:
        warnings: list[str] = []
        if document is None:
            warnings.append("No extracted document content is available for this input.")
        elif document.warnings:
            warnings.extend(document.warnings)

        metadata = _metadata_text(source, document)
        chunks = (
            evidence_prompt_context(document) if document is not None else "(no chunks available)"
        )
        source_text = _source_text(source) if source is not None else f"Input: {input_value}"
        document_text = _document_text(document) if document is not None else "(no document)"
        input_text = chunks if document is not None else source_text
        return {
            "profile": profile,
            "source": source_text,
            "document": document_text,
            "metadata": metadata,
            "chunks": chunks,
            "evidence_instructions": _evidence_instructions(document),
            "output_schema": output_schema,
            "warnings": "\n".join(f"- {warning}" for warning in warnings) or "(none)",
            "input_text": input_text,
            "source_id": source.id if source else "",
            "source_type": source.source_type if source else "file",
            "title": (
                (source.title if source else None)
                or (document.title if document else None)
                or "(untitled)"
            ),
            "target": source.target if source else input_value,
            "tags": ", ".join(source.tags) if source and source.tags else "(none)",
            "domain": source.url.domain if source and source.url else "(not applicable)",
        }

    def _file_context(
        self, input_value: str, *, profile: str, output_schema: str
    ) -> dict[str, str]:
        path = Path(input_value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if path.exists() and path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            text = path.read_text(encoding="utf-8")[:12000]
        elif path.exists():
            text = f"[File exists but was not parsed: {path}]"
        else:
            text = f"[No file, source, or document found for input: {input_value}]"
        return {
            "profile": profile,
            "source": f"File input: {path}",
            "document": "(no document)",
            "metadata": f"path: {path}",
            "chunks": text,
            "evidence_instructions": "Cite only excerpts present in the input.",
            "output_schema": output_schema,
            "warnings": "(none)" if path.exists() else "- Input was not found.",
            "input_text": text,
            "source_id": "",
            "source_type": "file",
            "title": path.name,
            "target": str(path),
            "tags": "(none)",
            "domain": "(not applicable)",
        }

    def _workspace_skills(self) -> list[Skill]:
        skills_dir = self.workspace / "skills"
        if not skills_dir.exists():
            return []

        skills: list[Skill] = []
        paths = sorted(skills_dir.glob("*/*.yaml")) + sorted(skills_dir.glob("*/skill.yaml"))
        seen_paths: set[Path] = set()
        for path in paths:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            skill = _load_skill_file(path, skills_dir)
            if skill is not None:
                skills.append(skill)
        return skills


def _load_skill_file(path: Path, skills_dir: Path) -> Skill | None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return None
    category = str(data.get("category") or path.parent.name)
    name = str(data.get("name") or (path.parent.name if path.name == "skill.yaml" else path.stem))
    prompt_value = str(data.get("prompt_template") or data.get("prompt") or "prompt.md")
    prompt_path = path.parent / prompt_value
    prompt_template = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else prompt_value
    )
    if not prompt_template.strip():
        return None
    return Skill(
        name=name,
        category=category,
        description=str(data.get("description", "Workspace skill.")),
        input_type=str(data.get("input_type", "text")),
        output_type=str(data.get("output_type", "markdown")),
        required_context=list(data.get("required_context", [])),
        recommended_model=str(
            data.get("recommended_model", data.get("recommended_model_tier", "optional"))
        ),
        version=str(data.get("version", "0.1")),
        author=data.get("author"),
        tags=list(data.get("tags", [])),
        inputs=list(data.get("inputs", [])),
        outputs=list(data.get("outputs", [])),
        recommended_model_tier=str(
            data.get("recommended_model_tier", data.get("recommended_model", "optional"))
        ),
        prompt_template=prompt_template,
        origin="workspace" if path.is_relative_to(skills_dir) else "built-in",
    )


def _try_get_source(registry: SourceRegistry, source_id: str) -> Source | None:
    try:
        return registry.get(source_id)
    except SourceNotFoundError:
        return None


def _metadata_text(source: Source | None, document: Document | None) -> str:
    data: dict[str, Any] = {}
    if source is not None:
        data.update(
            {
                "source_id": source.id,
                "source_type": source.source_type,
                "title": source.title,
                "target": source.target,
                "authors": source.authors,
                "published_at": source.published_at.isoformat() if source.published_at else None,
                "external_id": source.external_id,
                "tags": source.tags,
                "abstract": source.abstract,
            }
        )
    if document is not None:
        data.update(
            {
                "document_id": document.id,
                "content_type": document.content_type,
                "extraction_status": document.extraction_status,
                "text_path": document.text_path,
                "warnings": document.warnings,
            }
        )
    return yaml.safe_dump(data or {"input": "unknown"}, sort_keys=False).strip()


def _source_text(source: Source | None) -> str:
    if source is None:
        return "(no source)"
    lines = [
        f"- source_id: {source.id}",
        f"- type: {source.source_type}",
        f"- title: {source.title or '(untitled)'}",
        f"- target: {source.target}",
        f"- tags: {', '.join(source.tags) if source.tags else '(none)'}",
    ]
    if source.url is not None:
        lines.append(f"- domain: {source.url.domain or '(unknown)'}")
    return "\n".join(lines)


def _document_text(document: Document | None) -> str:
    if document is None:
        return "(no document)"
    return "\n".join(
        [
            f"- document_id: {document.id}",
            f"- source_id: {document.source_id}",
            f"- content_type: {document.content_type}",
            f"- extraction_status: {document.extraction_status}",
            f"- text_path: {document.text_path}",
            f"- chunks: {len(document.chunks)}",
        ]
    )


def _evidence_instructions(document: Document | None) -> str:
    if document is None:
        return "No extracted document is available. Do not fabricate evidence spans."
    return (
        "Use the provided chunks as evidence. Cite observations with document_id and chunk_id. "
        "Do not claim unsupported results, experiments, datasets, or citations."
    )


def _default_output_schema(skill: Skill) -> str:
    if skill.output_type == "paper_card_markdown":
        return (
            "- Metadata\n- Summary\n- Evidence\n- Limitations and missing evidence\n"
            "- Claims not yet supported\n- Follow-up questions"
        )
    return f"Markdown output for {skill.output_type}."
