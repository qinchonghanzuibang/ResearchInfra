from pathlib import Path

import yaml

from researchinfra.cli import run


def _create_project(workspace: Path, capsys) -> tuple[str, Path]:  # type: ignore[no-untyped-def]
    assert (
        run(
            [
                "project",
                "create",
                "--workspace",
                str(workspace),
                "--name",
                "Evidence Loop",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    project_id = next(
        line.split(": ", 1)[1] for line in output.splitlines() if line.startswith("Created Project")
    )
    return project_id, workspace / "projects" / project_id.removeprefix("project-")


def _plan_and_add_run(workspace: Path, project_id: str, capsys) -> str:  # type: ignore[no-untyped-def]
    assert run(["experiment", "plan", "--project", project_id, "--workspace", str(workspace)]) == 0
    capsys.readouterr()
    assert run(["experiment", "list", "--project", project_id, "--workspace", str(workspace)]) == 0
    experiment_id = capsys.readouterr().out.strip()
    assert (
        run(
            [
                "experiment",
                "add-run",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--experiment",
                experiment_id,
                "--metric",
                "smoke_check=passed",
            ]
        )
        == 0
    )
    capsys.readouterr()
    return experiment_id


def test_model_registry_commands_hide_secrets(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()

    assert run(["model", "list", "--workspace", str(workspace)]) == 0
    list_output = capsys.readouterr().out
    assert "openai-compatible" in list_output
    assert "example.invalid" not in list_output

    assert (
        run(
            [
                "model",
                "set-default",
                "--workspace",
                str(workspace),
                "--task",
                "reading",
                "--provider",
                "openai-compatible",
                "--model",
                "demo-reading-model",
            ]
        )
        == 0
    )
    assert "demo-reading-model" in capsys.readouterr().out

    code = run(["model", "test", "--workspace", str(workspace), "--task", "reading"])
    output = capsys.readouterr().out
    assert code == 2
    assert "OPENAI_API_KEY" in output
    assert "secret" not in output.lower()

    config = yaml.safe_load((workspace / ".researchinfra" / "workspace.yaml").read_text())
    assert config["model_defaults"]["reading"] == "openai-compatible"


def test_results_claims_paper_and_agent_loop(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    project_id, project_dir = _create_project(workspace, capsys)
    _plan_and_add_run(workspace, project_id, capsys)

    assert run(["result", "list", "--project", project_id, "--workspace", str(workspace)]) == 0
    assert "smoke_check" in capsys.readouterr().out

    assert run(["result", "summarize", "--project", project_id, "--workspace", str(workspace)]) == 0
    assert (project_dir / "results" / "summary.md").exists()

    assert (
        run(
            [
                "table",
                "create",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--from-runs",
            ]
        )
        == 0
    )
    assert "Created Table" in capsys.readouterr().out
    table_yaml = (project_dir / "tables" / "table-runs.yaml").read_text(encoding="utf-8")
    assert "run-0001" in table_yaml
    assert "smoke_check" in table_yaml

    assert (
        run(
            [
                "figure",
                "create",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--title",
                "Evidence Flow",
            ]
        )
        == 0
    )
    figure_yaml = (project_dir / "figures" / "figure-evidence-flow.yaml").read_text(
        encoding="utf-8"
    )
    assert "run-0001" in figure_yaml

    draft = project_dir / "draft" / "claim_draft.md"
    draft.write_text(
        "The smoke check is recorded in run-0001. We outperform all baselines.",
        encoding="utf-8",
    )
    assert (
        run(
            [
                "claim",
                "check",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--draft",
                str(draft),
                "--dry-run",
            ]
        )
        == 0
    )
    assert "Possible overclaim" in capsys.readouterr().out

    assert (
        run(
            [
                "claim",
                "check",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--draft",
                str(draft),
            ]
        )
        == 0
    )
    assert (project_dir / "claims" / "claim_report.md").exists()
    assert (project_dir / "claims" / "claim_evidence.yaml").exists()

    assert (
        run(
            [
                "paper",
                "init",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--venue",
                "arxiv",
            ]
        )
        == 0
    )
    assert (project_dir / "paper" / "arxiv" / "main.tex").exists()

    assert (
        run(
            [
                "paper",
                "check",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--venue",
                "arxiv",
            ]
        )
        == 0
    )
    paper_check = capsys.readouterr().out
    assert "Paper Check" in paper_check
    assert "LaTeX tools" in paper_check or "Warnings" in paper_check

    assert (
        run(
            [
                "paper",
                "package",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--venue",
                "arxiv",
                "--arxiv",
            ]
        )
        == 0
    )
    assert (project_dir / "submissions" / "arxiv" / "arxiv" / "package.yaml").exists()

    assert (
        run(
            [
                "agent",
                "task",
                "create",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--type",
                "writing",
                "--title",
                "Review claim report",
            ]
        )
        == 0
    )
    task_output = capsys.readouterr().out
    task_id = next(
        line.split(": ", 1)[1]
        for line in task_output.splitlines()
        if line.startswith("Created Agent Task")
    )

    assert (
        run(
            [
                "agent",
                "run",
                task_id,
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--backend",
                "manual",
                "--dry-run",
            ]
        )
        == 0
    )
    manual_output = capsys.readouterr().out
    assert "# Manual Agent Task:" in manual_output
    assert "instructions:" not in manual_output

    assert (
        run(
            [
                "agent",
                "run",
                task_id,
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--backend",
                "manual",
                "--dry-run",
                "--format",
                "yaml",
            ]
        )
        == 0
    )
    assert "instructions:" in capsys.readouterr().out

    assert (
        run(
            [
                "agent",
                "run",
                task_id,
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--backend",
                "manual",
            ]
        )
        == 0
    )
    assert (project_dir / "agents" / "results" / f"{task_id}-manual.yaml").exists()


def test_v1_demo_workspace_integrity() -> None:
    demo = Path(__file__).resolve().parents[1] / "examples" / "v1-loop"
    required = [
        "README.md",
        "sources/demo-source.md",
        "memory/documents/doc-demo-source/text.md",
        "memory/readings/reading-demo-source/notes.md",
        "memory/papers/paper-demo-source.md",
        "memory/ideas/idea-evidence-loop.md",
        "projects/evidence-loop/project.yaml",
        "projects/evidence-loop/experiments/experiment_plan.md",
        "projects/evidence-loop/experiments/run_registry.yaml",
        "projects/evidence-loop/results/result_bundle.yaml",
        "projects/evidence-loop/tables/table-runs.yaml",
        "projects/evidence-loop/figures/figure-evidence-flow.yaml",
        "projects/evidence-loop/draft/outline.md",
        "projects/evidence-loop/claims/claim_report.md",
        "projects/evidence-loop/paper/arxiv/check_report.md",
        "projects/evidence-loop/agents/tasks/task-writing-0001.yaml",
    ]
    missing = [path for path in required if not (demo / path).exists()]
    assert missing == []
    assert "not a scientific result" in (
        demo / "projects" / "evidence-loop" / "experiments" / "run_registry.yaml"
    ).read_text(encoding="utf-8")
