"""Project-local result, table, and figure registries."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

from researchinfra.schemas import (
    EvidenceLink,
    FigureRecord,
    MetricRecord,
    MetricValue,
    ResultBundle,
    Run,
    TableRecord,
)
from researchinfra.workflows import ProjectService, WorkflowError
from researchinfra.workspace_files import read_yaml_mapping, validate_yaml_records, write_yaml


class ResultRegistryError(WorkflowError):
    """Raised when result registries cannot be read or written."""


class ResultRegistry:
    """Build file-first registries from explicit project run records."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.projects = ProjectService(self.workspace)

    def list(self, project_id: str) -> ResultBundle:
        """Return the current bundle, refreshing run-grounded metrics first."""

        return self.collect(project_id)

    def summarize(self, project_id: str) -> tuple[ResultBundle, Path]:
        """Write a conservative Markdown summary of project results."""

        bundle = self.collect(project_id)
        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        path = base / "results" / "summary.md"
        lines = [
            f"# Result Summary: {project.title}",
            "",
            "> Metrics below are copied only from explicit run records.",
            "",
        ]
        if not bundle.metrics:
            lines.extend(
                [
                    "No run-grounded metrics are registered yet.",
                    "",
                    "Add runs with `researchinfra experiment add-run` before claiming results.",
                ]
            )
        else:
            lines.extend(["| Run | Experiment | Metric | Value |", "| --- | --- | --- | --- |"])
            for metric in bundle.metrics:
                lines.append(
                    f"| `{metric.run_id}` | `{metric.experiment_id}` | "
                    f"`{metric.name}` | {metric.value} |"
                )
        if bundle.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in bundle.warnings)
        path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return bundle, path

    def collect(self, project_id: str) -> ResultBundle:
        """Refresh metric and result bundle YAML from the run registry."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        result_dir = base / "results"
        result_dir.mkdir(parents=True, exist_ok=True)
        run_path = base / "experiments" / "run_registry.yaml"
        runs = self._read_runs(project_id)
        warnings = []
        if not runs:
            warnings.append("No run records are available; no result claims are supported.")
        metrics: list[MetricRecord] = []
        for run in runs:
            if not run.metrics:
                warnings.append(f"Run {run.id} has no metrics.")
                continue
            for name, value in run.metrics.items():
                metrics.append(
                    MetricRecord(
                        id=f"metric-{run.id}-{_slug(name)}",
                        project_id=project.id,
                        experiment_id=run.experiment_id,
                        run_id=run.id,
                        name=name,
                        value=value,
                        source_path=str(run_path.relative_to(self.workspace)),
                        evidence=[EvidenceLink(kind="run", ref=run.id)],
                    )
                )
        tables = [
            str(path.relative_to(self.workspace))
            for path in sorted((base / "tables").glob("*.yaml"))
        ]
        figures = [
            str(path.relative_to(self.workspace))
            for path in sorted((base / "figures").glob("*.yaml"))
        ]
        bundle = ResultBundle(
            id=f"result-bundle-{project.id.removeprefix('project-')}",
            project_id=project.id,
            metrics=metrics,
            tables=tables,
            figures=figures,
            warnings=warnings,
        )
        _write_yaml(
            result_dir / "metrics.yaml",
            {"project_id": project.id, "metrics": [m.model_dump(mode="json") for m in metrics]},
        )
        _write_yaml(result_dir / "result_bundle.yaml", bundle.model_dump(mode="json"))
        return bundle

    def create_table_from_runs(self, project_id: str) -> tuple[TableRecord, Path, Path]:
        """Create a table registry and Markdown table from recorded runs."""

        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        table_dir = base / "tables"
        table_dir.mkdir(parents=True, exist_ok=True)
        bundle = self.collect(project_id)
        runs = self._read_runs(project_id)
        metric_names = sorted({metric.name for metric in bundle.metrics})
        columns = ["run_id", "experiment_id", "status", *metric_names]
        rows: list[dict[str, MetricValue]] = []
        cell_evidence: dict[str, list[EvidenceLink]] = {}
        for run in runs:
            row: dict[str, MetricValue] = {
                "run_id": run.id,
                "experiment_id": run.experiment_id,
                "status": run.status,
            }
            for name in metric_names:
                if name in run.metrics:
                    row[name] = run.metrics[name]
                    cell_evidence[f"{run.id}:{name}"] = [EvidenceLink(kind="run", ref=run.id)]
                else:
                    row[name] = None
            rows.append(row)

        warnings = []
        if not rows:
            warnings.append("No run records are available; table contains no numeric results.")
        if not metric_names:
            warnings.append("No metrics are available; no result values were created.")
        markdown_path = table_dir / "table-runs.md"
        yaml_path = table_dir / "table-runs.yaml"
        table = TableRecord(
            id="table-runs",
            project_id=project.id,
            title="Run-grounded result table",
            path=str(markdown_path.relative_to(self.workspace)),
            source_run_ids=[run.id for run in runs],
            columns=columns,
            rows=rows,
            cell_evidence=cell_evidence,
            warnings=warnings,
        )
        _write_yaml(yaml_path, table.model_dump(mode="json"))
        markdown_path.write_text(_render_table_markdown(table) + "\n", encoding="utf-8")
        self.collect(project_id)
        return table, yaml_path, markdown_path

    def create_figure(self, project_id: str, *, title: str) -> tuple[FigureRecord, Path, Path]:
        """Create a figure placeholder linked to available run ids."""

        title = title.strip()
        if not title:
            raise ResultRegistryError("Figure title must not be empty.")
        project = self.projects.get(project_id)
        base = self.projects.path_for(project)
        figure_dir = base / "figures"
        figure_dir.mkdir(parents=True, exist_ok=True)
        runs = self._read_runs(project_id)
        figure_id = f"figure-{_slug(title)}"
        markdown_path = figure_dir / f"{figure_id}.md"
        yaml_path = figure_dir / f"{figure_id}.yaml"
        warnings = [
            "No visual artifact was generated. Add a real plot or figure file before citing it.",
        ]
        if not runs:
            warnings.append("No run ids are available to link as figure inputs.")
        figure = FigureRecord(
            id=figure_id,
            project_id=project.id,
            title=title,
            path=str(markdown_path.relative_to(self.workspace)),
            input_run_ids=[run.id for run in runs],
            input_paths=[
                str((base / "experiments" / "run_registry.yaml").relative_to(self.workspace))
            ]
            if runs
            else [],
            warnings=warnings,
        )
        _write_yaml(yaml_path, figure.model_dump(mode="json"))
        markdown_path.write_text(_render_figure_markdown(figure) + "\n", encoding="utf-8")
        self.collect(project_id)
        return figure, yaml_path, markdown_path

    def _read_runs(self, project_id: str) -> list[Run]:
        project = self.projects.get(project_id)
        path = self.projects.path_for(project) / "experiments" / "run_registry.yaml"
        data = _read_yaml(path)
        return validate_yaml_records(data, key="runs", model_type=Run, path=path)


def _render_table_markdown(table: TableRecord) -> str:
    lines = [f"# {table.title}", "", "> Every populated metric cell links to a run id.", ""]
    if not table.columns:
        lines.append("No columns are available.")
    else:
        lines.append("| " + " | ".join(table.columns) + " |")
        lines.append("| " + " | ".join("---" for _ in table.columns) + " |")
        for row in table.rows:
            values = [
                "" if row.get(column) is None else str(row.get(column)) for column in table.columns
            ]
            lines.append("| " + " | ".join(values) + " |")
    if table.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in table.warnings)
    return "\n".join(lines).strip()


def _render_figure_markdown(figure: FigureRecord) -> str:
    return dedent(
        f"""
        # {figure.title}

        - Figure ID: `{figure.id}`
        - Input run IDs: {", ".join(f"`{run_id}`" for run_id in figure.input_run_ids) or "none"}
        - Input paths: {", ".join(f"`{path}`" for path in figure.input_paths) or "none"}

        This is a registry placeholder. Add a real figure artifact before citing it in a draft.

        ## Warnings

        {_bullet_list(figure.warnings)}
        """
    ).strip()


def _read_yaml(path: Path) -> dict[str, object]:
    return read_yaml_mapping(path)


def _write_yaml(path: Path, data: object) -> None:
    write_yaml(path, data)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "untitled"


def _bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none"
