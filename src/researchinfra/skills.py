"""Reusable skill loading and prompt rendering."""

from __future__ import annotations

from pathlib import Path
from string import Template
from textwrap import dedent

import yaml

from researchinfra.schemas import Skill, Source
from researchinfra.sources import SourceNotFoundError, SourceRegistry


class SkillError(RuntimeError):
    """Base exception for skill operations."""


class SkillNotFoundError(SkillError):
    """Raised when a skill cannot be found."""


BUILTIN_SKILLS: dict[str, Skill] = {
    "paper_card": Skill(
        name="paper_card",
        description="Create an evidence-aware Paper Card from source metadata or notes.",
        inputs=["source"],
        outputs=["paper_card_markdown", "paper_metadata_yaml"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            You are helping create a ResearchInfra Paper Card.

            Source metadata:
            - source_id: $source_id
            - type: $source_type
            - title: $title
            - target: $target
            - tags: $tags
            - domain: $domain

            Available extracted text or notes:
            $input_text

            Write a structured Paper Card in Markdown with these sections:
            - Metadata
            - What is known from the provided metadata
            - Evidence available
            - Missing evidence and uncertainty
            - Claims not yet supported
            - Follow-up reading questions

            Important constraints:
            - Do not fabricate paper content, citations, experiments, datasets, metrics, or results.
            - If only metadata is available, explicitly warn that the card is metadata-limited.
            - Keep claims separate from hypotheses.
            """
        ).strip(),
    ),
    "idea_card": Skill(
        name="idea_card",
        description="Generate a cautious Idea Card from a Paper Card or source context.",
        inputs=["paper_card"],
        outputs=["idea_card_markdown", "idea_metadata_yaml"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            You are helping create a ResearchInfra Idea Card.

            Input context:
            $input_text

            Write a structured Idea Card in Markdown with these sections:
            - Motivation
            - Research question
            - Hypothesis
            - Evidence needed
            - Possible experiments
            - Risks and uncertainty
            - Human review checklist

            Important constraints:
            - Do not invent results, citations, or experiments as completed work.
            - Mark all proposed experiments as proposals, not evidence.
            - Explicitly warn when the idea is based only on limited metadata.
            """
        ).strip(),
    ),
    "claim_check": Skill(
        name="claim_check",
        description="Check whether a claim is supported by available workspace evidence.",
        inputs=["claim_or_note"],
        outputs=["claim_review"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Review the following claim or note against available context:

            $input_text

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
        description="Draft an experiment plan from a research idea or claim.",
        inputs=["idea_or_claim"],
        outputs=["experiment_plan"],
        recommended_model_tier="standard",
        prompt_template=dedent(
            """
            Draft a ResearchInfra experiment plan from this context:

            $input_text

            Include:
            - Question
            - Hypothesis
            - Required datasets or sources
            - Baselines to define before running
            - Metrics to justify
            - Artifacts to record
            - Risks, confounders, and missing evidence

            Do not present any proposed experiment as already run.
            """
        ).strip(),
    ),
}


class SkillRunner:
    """Load skills and render prompts from workspace inputs."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry = SourceRegistry(self.workspace)

    def list(self) -> list[Skill]:
        """Return built-in and workspace skills."""

        skills = {name: skill for name, skill in BUILTIN_SKILLS.items()}
        for skill in self._workspace_skills():
            skills[skill.name] = skill
        return sorted(skills.values(), key=lambda skill: skill.name)

    def get(self, name: str) -> Skill:
        """Return a skill by name."""

        for skill in self.list():
            if skill.name == name:
                return skill
        raise SkillNotFoundError(f"Skill not found: {name}")

    def render(self, name: str, input_value: str) -> str:
        """Render a skill prompt for a file path or source id."""

        skill = self.get(name)
        context = self._input_context(input_value)
        return Template(skill.prompt_template).safe_substitute(context)

    def _workspace_skills(self) -> list[Skill]:
        skills_dir = self.workspace / "skills"
        if not skills_dir.exists():
            return []

        skills: list[Skill] = []
        for path in sorted(skills_dir.glob("*/skill.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                continue
            prompt_path = path.parent / str(data.get("prompt", "prompt.md"))
            prompt_template = (
                prompt_path.read_text(encoding="utf-8")
                if prompt_path.exists()
                else str(data.get("prompt_template", ""))
            )
            if not prompt_template.strip():
                continue
            skills.append(
                Skill(
                    name=str(data.get("name", path.parent.name)),
                    description=str(data.get("description", "Workspace skill.")),
                    inputs=list(data.get("inputs", [])),
                    outputs=list(data.get("outputs", [])),
                    recommended_model_tier=str(data.get("recommended_model_tier", "optional")),
                    prompt_template=prompt_template,
                    origin="workspace",
                )
            )
        return skills

    def _input_context(self, input_value: str) -> dict[str, str]:
        try:
            source = self.registry.get(input_value)
        except SourceNotFoundError:
            return self._file_context(input_value)
        return self._source_context(source)

    def _source_context(self, source: Source) -> dict[str, str]:
        domain = source.url.domain if source.url is not None else ""
        return {
            "source_id": source.id,
            "source_type": source.source_type,
            "title": source.title or "(untitled)",
            "target": source.target,
            "tags": ", ".join(source.tags) if source.tags else "(none)",
            "domain": domain or "(not applicable)",
            "input_text": _metadata_limited_text(source),
        }

    def _file_context(self, input_value: str) -> dict[str, str]:
        path = Path(input_value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        text = ""
        if path.exists() and path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            text = path.read_text(encoding="utf-8")[:12000]
        elif path.exists():
            text = f"[File exists but was not parsed: {path}]"
        else:
            text = f"[No file or source found for input: {input_value}]"
        return {
            "source_id": "",
            "source_type": "file",
            "title": path.name,
            "target": str(path),
            "tags": "(none)",
            "domain": "(not applicable)",
            "input_text": text,
        }


def _metadata_limited_text(source: Source) -> str:
    lines = [
        "WARNING: This context is based only on source metadata unless separate notes were added.",
        f"Source id: {source.id}",
        f"Title: {source.title or '(untitled)'}",
        f"Type: {source.source_type}",
        f"Target: {source.target}",
    ]
    if source.local is not None:
        size = source.local.size_bytes if source.local.size_bytes is not None else "(unknown)"
        lines.extend(
            [
                f"Filename: {source.local.filename}",
                f"Extension: {source.local.extension or '(none)'}",
                f"Size bytes: {size}",
            ]
        )
    if source.url is not None:
        lines.append(f"Domain: {source.url.domain or '(unknown)'}")
    return "\n".join(lines)
