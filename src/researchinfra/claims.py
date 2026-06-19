"""Evidence checks for project claims and draft text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from researchinfra.schemas import Claim, EvidenceLink, Run, utc_now
from researchinfra.workflows import ProjectService, WorkflowError
from researchinfra.workspace_files import (
    read_yaml_mapping,
    validate_yaml_model,
    validate_yaml_records,
    write_yaml,
)


class ClaimCheckError(WorkflowError):
    """Raised when claim checks cannot be completed."""


RESULT_WORDS = re.compile(
    r"\b(achieve|achieves|achieved|accuracy|score|result|results|improve|improves|"
    r"outperform|outperforms|beat|beats|better|best|state[- ]of[- ]the[- ]art|sota)\b",
    re.IGNORECASE,
)
COMPARISON_WORDS = re.compile(
    r"\b(outperform|outperforms|beat|beats|better|best|improve|improves|SOTA|"
    r"state[- ]of[- ]the[- ]art)\b",
    re.IGNORECASE,
)
OOD_WORDS = re.compile(r"\b(ood|out[- ]of[- ]distribution|robust|generaliz|ablation)\b", re.I)
RUN_ID = re.compile(r"\brun-\d{4}\b")


@dataclass(frozen=True)
class CheckedClaim:
    """A claim plus conservative support status."""

    claim_id: str
    text: str
    status: str
    evidence: list[EvidenceLink]
    warnings: list[str]


@dataclass(frozen=True)
class ClaimCheckResult:
    """Rendered and structured output for a claim check."""

    project_id: str
    claims: list[CheckedClaim]
    warnings: list[str]
    report: str
    report_path: Path | None = None
    evidence_path: Path | None = None


class ClaimService:
    """List and check project claims against local evidence registries."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)

    def list(self, project_id: str) -> list[str]:
        """Return project-linked claims or checked claim ids."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        checked = _read_yaml(base / "claims" / "claim_evidence.yaml")
        if isinstance(checked.get("claims"), list) and checked["claims"]:
            return [
                str(item.get("claim_id", "claim")) + ": " + str(item.get("text", ""))
                for item in checked["claims"]
                if isinstance(item, dict)
            ]
        return list(project.claims)

    def check(
        self,
        project_id: str,
        *,
        draft: str | Path | None = None,
        dry_run: bool = False,
    ) -> ClaimCheckResult:
        """Check whether claims have explicit local evidence."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        claims = self._collect_claims(project_id, draft=draft)
        run_ids = self._run_ids(project_id)
        baselines = self._registry_items(
            base / "experiments" / "baseline_registry.yaml",
            "baselines",
        )
        ablations = self._registry_items(base / "experiments" / "ablation_matrix.yaml", "ablations")
        has_plan = (base / "experiments" / "experiment_plan.md").exists()
        global_warnings: list[str] = []
        if not baselines:
            global_warnings.append("Missing baselines: comparison claims are not supported yet.")
        if not ablations:
            global_warnings.append(
                "Missing OOD/ablation evidence: robustness claims need more support."
            )
        if not run_ids:
            global_warnings.append("No run records found: result claims are unsupported.")

        checked: list[CheckedClaim] = []
        for index, text in enumerate(claims, start=1):
            claim_id = f"claim-{index:04d}"
            evidence: list[EvidenceLink] = []
            warnings: list[str] = []
            referenced_runs = [run_id for run_id in RUN_ID.findall(text) if run_id in run_ids]
            for run_id in referenced_runs:
                evidence.append(EvidenceLink(kind="run", ref=run_id))

            if has_plan and "plan" in text.lower():
                evidence.append(EvidenceLink(kind="experiment", ref="experiment_plan.md"))

            if RESULT_WORDS.search(text) and not referenced_runs:
                warnings.append("Result claim does not cite an existing run id.")
            if COMPARISON_WORDS.search(text) and not baselines:
                warnings.append(
                    "Possible overclaim: comparison language appears without baselines."
                )
            if OOD_WORDS.search(text) and not ablations:
                warnings.append("OOD/ablation claim lacks ablation or robustness evidence.")
            if not evidence:
                warnings.append(
                    "Unsupported claim: no explicit paper, reading, plan, table, figure, "
                    "or run link."
                )

            status = (
                "supported" if evidence and not warnings else "partial" if evidence else "missing"
            )
            checked.append(
                CheckedClaim(
                    claim_id=claim_id,
                    text=text,
                    status=status,
                    evidence=evidence,
                    warnings=warnings,
                )
            )

        if not checked:
            global_warnings.append("No claims found in project metadata or draft text.")
        if any(item.status == "missing" for item in checked):
            global_warnings.append("Unsupported claims remain before submission.")

        report = _render_report(project.id, checked, global_warnings)
        if dry_run:
            return ClaimCheckResult(
                project_id=project.id,
                claims=checked,
                warnings=global_warnings,
                report=report,
            )

        claim_dir = base / "claims"
        report_path = claim_dir / "claim_report.md"
        evidence_path = claim_dir / "claim_evidence.yaml"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report + "\n", encoding="utf-8")
        evidence = _evidence_payload(project.id, checked, global_warnings)
        _write_yaml(evidence_path, evidence)
        _write_yaml(base / "experiments" / "claim_evidence.yaml", evidence)
        return ClaimCheckResult(
            project_id=project.id,
            claims=checked,
            warnings=global_warnings,
            report=report,
            report_path=report_path,
            evidence_path=evidence_path,
        )

    def _collect_claims(self, project_id: str, *, draft: str | Path | None) -> list[str]:
        project = self.projects.get(project_id)
        claims: list[str] = []
        for claim_ref in project.claims:
            resolved = self._resolve_claim(claim_ref)
            claims.append(resolved)
        if draft is not None:
            path = Path(draft).expanduser()
            if not path.is_absolute():
                path = (self.workspace / path).resolve()
            if not path.exists():
                raise ClaimCheckError(f"Draft not found: {path}")
            claims.extend(_extract_claim_sentences(path.read_text(encoding="utf-8")))
        return _dedupe([claim for claim in claims if claim.strip()])

    def _resolve_claim(self, claim_ref: str) -> str:
        path = self.workspace / "memory" / "claims" / f"{claim_ref}.yaml"
        if path.exists():
            return validate_yaml_model(Claim, _read_yaml(path), path=path).text
        return claim_ref

    def _run_ids(self, project_id: str) -> set[str]:
        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        data = _read_yaml(base / "experiments" / "run_registry.yaml")
        run_path = base / "experiments" / "run_registry.yaml"
        runs = validate_yaml_records(data, key="runs", model_type=Run, path=run_path)
        return {run.id for run in runs}

    def _registry_items(self, path: Path, key: str) -> list[object]:
        data = _read_yaml(path)
        raw = data.get(key, []) if isinstance(data, dict) else []
        return raw if isinstance(raw, list) else []


def _extract_claim_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    candidates = []
    for sentence in sentences:
        stripped = sentence.strip()
        if len(stripped) < 20:
            continue
        if (
            RESULT_WORDS.search(stripped)
            or OOD_WORDS.search(stripped)
            or "claim" in stripped.lower()
        ):
            candidates.append(stripped)
    return candidates


def _render_report(project_id: str, claims: list[CheckedClaim], warnings: list[str]) -> str:
    lines = [
        f"# Claim Report: {project_id}",
        "",
        "> Conservative check: unsupported claims must be revised or linked before submission.",
        "",
    ]
    if not claims:
        lines.append("No claims were found.")
    for claim in claims:
        lines.extend(
            [
                f"## {claim.claim_id}",
                "",
                claim.text,
                "",
                f"- Status: `{claim.status}`",
                "- Evidence: "
                + (
                    ", ".join(f"`{item.kind}:{item.ref}`" for item in claim.evidence)
                    if claim.evidence
                    else "none"
                ),
                "- Warnings:",
                _indented_bullets(claim.warnings),
                "",
            ]
        )
    lines.extend(["## Global Warnings", "", _indented_bullets(warnings)])
    return "\n".join(lines).strip()


def _evidence_payload(
    project_id: str, claims: list[CheckedClaim], warnings: list[str]
) -> dict[str, object]:
    return {
        "project_id": project_id,
        "generated_at": utc_now().isoformat(),
        "claims": [
            {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "status": claim.status,
                "evidence": [item.model_dump(mode="json") for item in claim.evidence],
                "warnings": claim.warnings,
            }
            for claim in claims
        ],
        "warnings": warnings,
    }


def _read_yaml(path: Path) -> dict[str, object]:
    return read_yaml_mapping(path)


def _write_yaml(path: Path, data: object) -> None:
    write_yaml(path, data)


def _indented_bullets(values: list[str]) -> str:
    return "\n".join(f"  - {value}" for value in values) if values else "  - none"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
