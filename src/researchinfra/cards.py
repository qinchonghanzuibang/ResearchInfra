"""Paper Card and Idea Card generation."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import yaml

from researchinfra.documents import DocumentStore
from researchinfra.models.base import ModelProviderConfigurationError, ModelProviderRequestError
from researchinfra.models.dispatcher import ModelDispatcher
from researchinfra.schemas import Source, utc_now
from researchinfra.skills import SkillRunner
from researchinfra.sources import SourceRegistry


class CardError(RuntimeError):
    """Base exception for card generation."""


class PaperCardService:
    """Create file-first Paper Cards from sources."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry = SourceRegistry(self.workspace)
        self.runner = SkillRunner(self.workspace)
        self.documents = DocumentStore(self.workspace)

    def render_prompt(self, source_id: str, *, use_content: bool = False) -> str:
        """Render the Paper Card prompt for a source."""

        return self.runner.render(
            "paper_card",
            source_id,
            include_document=use_content,
        )

    def create(self, source_id: str, *, use_content: bool = False) -> tuple[str, Path, Path]:
        """Create a Paper Card markdown file and YAML metadata."""

        source = self.registry.get(source_id)
        paper_id = f"paper-{source.id.removeprefix('src-')}"
        document = self.documents.find_by_source_id(source_id) if use_content else None
        prompt = self.render_prompt(source_id, use_content=use_content)
        content = _complete_or_metadata_skeleton(
            prompt,
            workspace=self.workspace,
            task="reading",
            fallback=_paper_fallback_markdown(
                paper_id, source, document_id=document.id if document else None
            ),
        )
        metadata = {
            "id": paper_id,
            "source_id": source.id,
            "document_id": document.id if document else None,
            "title": source.title,
            "source_type": source.source_type,
            "target": source.target,
            "created_at": utc_now().isoformat(),
            "warning": "This card may be based only on limited metadata, not full paper text.",
        }
        base = self.workspace / "memory" / "papers"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{paper_id}.md"
        yaml_path = base / f"{paper_id}.yaml"
        _write_card(markdown_path, metadata, content)
        yaml_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
        return paper_id, markdown_path, yaml_path


class IdeaCardService:
    """Create file-first Idea Cards from Paper Cards."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.runner = SkillRunner(self.workspace)

    def generate(self, paper_id: str) -> tuple[str, Path, Path]:
        """Generate an Idea Card from a Paper Card."""

        paper_path = self.workspace / "memory" / "papers" / f"{paper_id}.md"
        if not paper_path.exists():
            raise CardError(f"Paper Card not found: {paper_id}")

        idea_id = f"idea-{_slug(paper_id)}"
        prompt = self.runner.render("idea_card", str(paper_path))
        content = _complete_or_metadata_skeleton(
            prompt,
            workspace=self.workspace,
            task="reasoning",
            fallback=_idea_fallback_markdown(idea_id, paper_id, paper_path),
        )
        metadata = {
            "id": idea_id,
            "from_paper": paper_id,
            "created_at": utc_now().isoformat(),
            "warning": "This idea may be based only on limited metadata, not full paper text.",
        }
        base = self.workspace / "memory" / "ideas"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{idea_id}.md"
        yaml_path = base / f"{idea_id}.yaml"
        _write_card(markdown_path, metadata, content)
        yaml_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
        return idea_id, markdown_path, yaml_path


def _complete_or_metadata_skeleton(
    prompt: str, *, workspace: Path, task: str, fallback: str
) -> str:
    try:
        provider = ModelDispatcher(workspace).provider_for_task(task)
    except ModelProviderConfigurationError as exc:
        raise CardError(str(exc)) from exc
    if provider is None:
        return fallback
    try:
        result = provider.complete(prompt)
    except (ModelProviderConfigurationError, ModelProviderRequestError) as exc:
        raise CardError(str(exc)) from exc
    if result.text:
        return _ensure_warning(result.text)
    return fallback


def _paper_fallback_markdown(paper_id: str, source: Source, *, document_id: str | None) -> str:
    evidence_text = (
        f"Extracted document `{document_id}` is available. Review its chunks before making claims."
        if document_id
        else "No extracted document content has been attached yet."
    )
    return dedent(
        f"""
        # Paper Card: {source.title or paper_id}

        > WARNING: This Paper Card is based only on limited source metadata. It does not
        > include full paper text, verified citations, experiments, datasets, metrics, or
        > results.

        ## Metadata

        - Paper ID: `{paper_id}`
        - Source ID: `{source.id}`
        - Type: `{source.source_type}`
        - Target: `{source.target}`

        ## What Is Known

        The workspace currently records this source and any manually provided title or tags.

        ## Evidence

        {evidence_text}

        Any future claim must cite explicit document chunks, papers, experiments, figures,
        tables, or run records.

        ## Missing Evidence And Uncertainty

        Add paper notes, extracted text, BibTeX, or manual annotations before making claims.

        ## Claims Not Yet Supported

        No scientific claims are supported by this metadata-only card.

        ## Follow-Up Reading Questions

        - What problem does the source address?
        - What evidence does the source provide?
        - Which claims should be linked to papers, experiments, figures, tables, or runs?
        """
    ).strip()


def _idea_fallback_markdown(idea_id: str, paper_id: str, paper_path: Path) -> str:
    return dedent(
        f"""
        # Idea Card: {idea_id}

        > WARNING: This Idea Card is based only on the current Paper Card context. It may be
        > metadata-limited and must be reviewed by a human before becoming a project plan.

        ## Motivation

        Review `{paper_id}` and identify a grounded research gap after adding real notes.

        ## Research Question

        What question follows from the evidence in `{paper_path.name}`?

        ## Hypothesis

        No hypothesis is supported yet.

        ## Evidence Needed

        - Full paper notes or extracted text.
        - Related papers.
        - Explicit claims and evidence links.

        ## Possible Experiments

        No experiments are proposed as completed work. Add candidate experiments only after
        defining baselines, datasets, metrics, and expected artifacts.

        ## Risks And Uncertainty

        This card should not be used as evidence until reviewed.

        ## Human Review Checklist

        - Confirm the idea is grounded in real source content.
        - Separate hypotheses from supported claims.
        - Link any future claims to evidence records.
        """
    ).strip()


def _write_card(path: Path, metadata: dict[str, object], content: str) -> None:
    front_matter = yaml.safe_dump(metadata, sort_keys=False).strip()
    path.write_text(f"---\n{front_matter}\n---\n\n{content}\n", encoding="utf-8")


def _ensure_warning(content: str) -> str:
    if "WARNING" in content.upper() and "metadata" in content.lower():
        return content
    warning = (
        "> WARNING: This generated card may be based only on limited metadata rather "
        "than full paper text. Verify all claims before use.\n\n"
    )
    return warning + content


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "untitled"
