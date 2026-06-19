"""Lightweight LaTeX and submission workflows."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from textwrap import dedent

from researchinfra.claims import ClaimService
from researchinfra.workflows import VENUES, ProjectService, WorkflowError
from researchinfra.workspace_files import read_yaml_mapping, write_yaml


class SubmissionError(WorkflowError):
    """Raised when a paper or submission operation fails."""


class SubmissionService:
    """Project-local paper initialization, checks, builds, and packages."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)

    def init(self, project_id: str, *, venue: str) -> tuple[Path, Path]:
        """Create a venue-specific LaTeX placeholder for a project."""

        _validate_venue(venue)
        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        paper_dir = base / "paper" / venue
        paper_dir.mkdir(parents=True, exist_ok=True)
        tex_path = paper_dir / "main.tex"
        metadata_path = paper_dir / "metadata.yaml"
        if not tex_path.exists():
            tex_path.write_text(_template_tex(project.title, venue) + "\n", encoding="utf-8")
        _write_yaml(
            metadata_path,
            {
                "project_id": project.id,
                "venue": venue,
                "anonymous": True,
                "camera_ready": False,
                "arxiv": venue == "arxiv",
                "notes": "Placeholder metadata; review before submission.",
            },
        )
        return tex_path, metadata_path

    def check(self, project_id: str, *, venue: str | None = None) -> tuple[list[str], Path]:
        """Write a conservative paper check report."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        selected_venue = venue or project.target_venue or _first_existing_venue(base) or "arxiv"
        _validate_venue(selected_venue)
        paper_dir = base / "paper" / selected_venue
        tex_path = paper_dir / "main.tex"
        warnings: list[str] = []
        if not tex_path.exists():
            warnings.append(
                f"Missing paper template: run `researchinfra paper init --venue {selected_venue}`."
            )
            text = ""
        else:
            text = tex_path.read_text(encoding="utf-8")
            warnings.extend(_section_warnings(text))
            warnings.extend(_citation_warnings(text))
            warnings.extend(_reference_warnings(text))

        if not _has_results(base):
            warnings.append("Missing results: no run-grounded result bundle or metrics were found.")

        claim_result = ClaimService(self.workspace).check(project.id, dry_run=True)
        if any(item.status != "supported" for item in claim_result.claims):
            warnings.append("Unsupported or partial claims remain in the claim check.")
        warnings.extend(claim_result.warnings)

        metadata = _read_yaml(paper_dir / "metadata.yaml")
        if selected_venue != "arxiv" and not metadata.get("anonymous", True):
            warnings.append("Anonymous submission metadata is disabled; verify venue phase.")
        if metadata.get("camera_ready") and metadata.get("anonymous"):
            warnings.append("Camera-ready metadata should not remain anonymous.")
        if shutil.which("latexmk") is None and shutil.which("pdflatex") is None:
            warnings.append(
                "LaTeX tools were not found; install latexmk or pdflatex to build PDFs."
            )

        report_path = paper_dir / "check_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_check_report(project.id, selected_venue, warnings) + "\n")
        return warnings, report_path

    def build(self, project_id: str, *, venue: str | None = None) -> tuple[int, Path]:
        """Build a paper if local LaTeX tools are installed."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        selected_venue = venue or project.target_venue or _first_existing_venue(base) or "arxiv"
        _validate_venue(selected_venue)
        paper_dir = base / "paper" / selected_venue
        tex_path = paper_dir / "main.tex"
        if not tex_path.exists():
            raise SubmissionError(
                f"Paper not initialized for {selected_venue}. "
                "Run `researchinfra paper init --project ... --venue ...` first."
            )

        executable = shutil.which("latexmk")
        command = [executable, "-pdf", "-interaction=nonstopmode", "main.tex"] if executable else []
        if not command:
            executable = shutil.which("pdflatex")
            command = [executable, "-interaction=nonstopmode", "main.tex"] if executable else []
        if not command:
            raise SubmissionError(
                "LaTeX is not installed or not on PATH. Install a TeX distribution with "
                "`latexmk` or `pdflatex`, then rerun `researchinfra paper build`."
            )

        completed = subprocess.run(
            command,
            cwd=paper_dir,
            text=True,
            capture_output=True,
            check=False,
        )
        log_path = paper_dir / "build.log"
        log_path.write_text(
            f"$ {' '.join(command)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
            encoding="utf-8",
        )
        return completed.returncode, log_path

    def package(
        self,
        project_id: str,
        *,
        venue: str | None = None,
        anonymous: bool = False,
        camera_ready: bool = False,
        arxiv: bool = False,
    ) -> tuple[Path, Path]:
        """Create a local submission package directory and zip file."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        selected_venue = venue or project.target_venue or _first_existing_venue(base) or "arxiv"
        _validate_venue(selected_venue)
        paper_dir = base / "paper" / selected_venue
        tex_path = paper_dir / "main.tex"
        if not tex_path.exists():
            raise SubmissionError(
                f"Paper not initialized for {selected_venue}. "
                "Run `researchinfra paper init --project ... --venue ...` first."
            )
        phase = (
            "camera-ready"
            if camera_ready
            else "arxiv"
            if arxiv
            else "anonymous"
            if anonymous
            else "draft"
        )
        package_dir = base / "submissions" / selected_venue / phase
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tex_path, package_dir / "main.tex")
        metadata = {
            "project_id": project.id,
            "venue": selected_venue,
            "phase": phase,
            "anonymous": anonymous,
            "camera_ready": camera_ready,
            "arxiv": arxiv,
            "warnings": [
                "Package contains local placeholders only; verify official venue style files.",
                "Run claim and paper checks before upload.",
            ],
        }
        _write_yaml(package_dir / "package.yaml", metadata)
        (package_dir / "PACKAGE.md").write_text(_render_package_report(metadata) + "\n", "utf-8")
        zip_path = package_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package_dir.iterdir()):
                if path.is_file():
                    archive.write(path, arcname=path.name)
        return package_dir, zip_path


def _template_tex(title: str, venue: str) -> str:
    venue_name = venue.upper() if venue != "arxiv" else "arXiv"
    return dedent(
        rf"""
        % ResearchInfra {venue_name} placeholder.
        % Replace with the official venue style files before submission.
        \documentclass{{article}}
        \title{{{_tex_escape(title)}}}
        \author{{Anonymous ResearchInfra Workspace}}
        \begin{{document}}
        \maketitle

        \begin{{abstract}}
        TODO: Write an evidence-grounded abstract after claims and results are checked.
        \end{{abstract}}

        \section{{Introduction}}
        TODO: State the problem with citations.

        \section{{Related Work}}
        TODO: Cite linked paper cards and reading notes.

        \section{{Method}}
        TODO: Describe only implemented or clearly planned methods.

        \section{{Experiments}}
        TODO: Include only results linked to run records, tables, and figures.

        \section{{Limitations}}
        TODO: Record missing evidence and known failure modes.

        \bibliographystyle{{plain}}
        \bibliography{{references}}
        \end{{document}}
        """
    ).strip()


def _section_warnings(text: str) -> list[str]:
    warnings = []
    required = ("Introduction", "Related Work", "Method", "Experiments", "Limitations")
    for section in required:
        if not re.search(rf"\\section\*?\{{{re.escape(section)}\}}", text):
            warnings.append(f"Missing required section: {section}.")
    return warnings


def _citation_warnings(text: str) -> list[str]:
    warnings = []
    if "\\cite" not in text:
        warnings.append("Missing citations: no LaTeX citation commands were detected.")
    if "\\bibliography" not in text and "\\begin{thebibliography}" not in text:
        warnings.append("Missing bibliography declaration.")
    return warnings


def _reference_warnings(text: str) -> list[str]:
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    warnings = []
    for ref in re.findall(r"\\ref\{([^}]+)\}", text):
        if ref not in labels:
            warnings.append(f"Broken reference detected: {ref}.")
    return warnings


def _has_results(base: Path) -> bool:
    metrics = _read_yaml(base / "results" / "metrics.yaml")
    raw_metrics = metrics.get("metrics", []) if isinstance(metrics, dict) else []
    return isinstance(raw_metrics, list) and bool(raw_metrics)


def _render_check_report(project_id: str, venue: str, warnings: list[str]) -> str:
    return dedent(
        f"""
        # Paper Check: {project_id}

        - Venue: `{venue}`
        - Status: {"warnings" if warnings else "no blocking warnings detected"}

        ## Warnings

        {_bullet_list(warnings)}
        """
    ).strip()


def _render_package_report(metadata: dict[str, object]) -> str:
    return dedent(
        f"""
        # Submission Package

        - Project: `{metadata["project_id"]}`
        - Venue: `{metadata["venue"]}`
        - Phase: `{metadata["phase"]}`

        ## Warnings

        {_bullet_list([str(item) for item in metadata["warnings"]])}
        """
    ).strip()


def _first_existing_venue(base: Path) -> str | None:
    paper_dir = base / "paper"
    if not paper_dir.exists():
        return None
    for venue in VENUES:
        if (paper_dir / venue / "main.tex").exists():
            return venue
    return None


def _validate_venue(venue: str) -> None:
    if venue not in VENUES:
        raise SubmissionError(f"Unsupported venue: {venue}")


def _tex_escape(value: str) -> str:
    return value.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def _read_yaml(path: Path) -> dict[str, object]:
    return read_yaml_mapping(path)


def _write_yaml(path: Path, data: object) -> None:
    write_yaml(path, data)


def _bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none"
