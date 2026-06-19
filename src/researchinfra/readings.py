"""Paper reading workflows and durable reading-note artifacts."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import yaml

from researchinfra.models.base import (
    ModelProviderConfigurationError,
    ModelProviderRequestError,
)
from researchinfra.models.dispatcher import ModelDispatcher
from researchinfra.schemas import Source, utc_now
from researchinfra.skills import READING_MODES, SkillRunner
from researchinfra.sources import SourceRegistry


class ReadingError(RuntimeError):
    """Base exception for paper reading operations."""


READING_MODE_SKILLS: dict[str, str] = {mode: f"read_{mode}" for mode in READING_MODES}

READING_OUTPUT_SCHEMAS: dict[str, str] = {
    "skim": (
        "- Triage decision\n- Why it matters\n- Key evidence spans\n"
        "- Missing context\n- Next action"
    ),
    "deep": "- Problem\n- Method\n- Evidence\n- Assumptions\n- Limitations\n- Questions",
    "idea": "- Gaps\n- Possible ideas\n- Evidence needed\n- Risks\n- Human review checklist",
    "reviewer": (
        "- Summary\n- Strengths\n- Weaknesses\n- Missing experiments\n- Overclaims\n- Questions"
    ),
    "reproduce": "- Artifacts needed\n- Datasets\n- Models\n- Training\n- Evaluation\n- Risks",
    "related_work": (
        "- Citation-ready summary\n- Contribution\n- Compared work\n- Useful spans\n- Caveats"
    ),
}


class ReadingService:
    """Render and persist evidence-grounded paper reading notes."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry = SourceRegistry(self.workspace)
        self.runner = SkillRunner(self.workspace)

    def render_prompt(self, source_id: str, *, mode: str) -> str:
        """Render the prompt for a source and reading mode."""

        skill_name = _skill_for_mode(mode)
        return self.runner.render(
            skill_name,
            source_id,
            output_schema=READING_OUTPUT_SCHEMAS[mode],
            include_document=True,
        )

    def read(self, source_id: str, *, mode: str) -> tuple[str, Path, Path]:
        """Create a saved reading-note artifact."""

        source = self.registry.get(source_id)
        skill_name = _skill_for_mode(mode)
        prompt = self.render_prompt(source_id, mode=mode)
        warnings: list[str] = []
        try:
            provider = ModelDispatcher(self.workspace).provider_for_task("reading")
        except ModelProviderConfigurationError as exc:
            raise ReadingError(str(exc)) from exc

        if provider is not None:
            try:
                result = provider.complete(prompt)
            except ModelProviderConfigurationError as exc:
                raise ReadingError(str(exc)) from exc
            except ModelProviderRequestError as exc:
                raise ReadingError(str(exc)) from exc
            else:
                execution_status = "model_generated"
                content = result.text or ""
                if not content.strip():
                    execution_status = "prompt_only"
                    warnings.append("Model provider returned empty text; saved prompt-only notes.")
                    content = _prompt_only_notes(source, mode=mode, prompt=prompt)
        else:
            execution_status = "prompt_only"
            warnings.append("No model default is configured for reading; saved prompt-only notes.")
            content = _prompt_only_notes(source, mode=mode, prompt=prompt)

        return self._write(
            source,
            mode=mode,
            skill_name=skill_name,
            content=content,
            execution_status=execution_status,
            warnings=warnings,
        )

    def _write(
        self,
        source: Source,
        *,
        mode: str,
        skill_name: str,
        content: str,
        execution_status: str,
        warnings: list[str],
    ) -> tuple[str, Path, Path]:
        now = utc_now()
        reading_id = (
            f"reading-{mode}-{source.id.removeprefix('src-')}-{now.strftime('%Y%m%dT%H%M%SZ')}"
        )
        base = self.workspace / "memory" / "readings" / reading_id
        base.mkdir(parents=True, exist_ok=True)
        notes_path = base / "notes.md"
        metadata_path = base / "metadata.yaml"
        metadata = {
            "id": reading_id,
            "source_id": source.id,
            "mode": mode,
            "skill_name": skill_name,
            "execution_status": execution_status,
            "created_at": now.isoformat(),
            "notes_path": _relative(notes_path, self.workspace),
            "metadata_path": _relative(metadata_path, self.workspace),
            "warnings": warnings,
        }
        notes_path.write_text(content.strip() + "\n", encoding="utf-8")
        metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
        return reading_id, notes_path, metadata_path


def _skill_for_mode(mode: str) -> str:
    try:
        return READING_MODE_SKILLS[mode]
    except KeyError as exc:
        choices = ", ".join(READING_MODE_SKILLS)
        raise ReadingError(f"Unknown reading mode: {mode}. Choose one of: {choices}") from exc


def _prompt_only_notes(source: Source, *, mode: str, prompt: str) -> str:
    return dedent(
        f"""
        # Reading Notes: {source.title or source.id}

        > WARNING: No model provider was configured, so this artifact stores the rendered
        > ResearchInfra reading prompt and context. It is not a model-generated reading
        > and does not establish any paper claims.

        ## Metadata

        - Source ID: `{source.id}`
        - Mode: `{mode}`
        - Target: `{source.target}`

        ## Status

        No model call was made. A human or approved agent can use the prompt below to
        produce evidence-grounded notes.

        ## Rendered Prompt

        ```text
        {prompt}
        ```
        """
    ).strip()


def _relative(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace))
