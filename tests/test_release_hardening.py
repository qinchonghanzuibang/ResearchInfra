"""Regression coverage for public-alpha safety and release behavior."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from researchinfra.cli import run


@pytest.mark.parametrize(
    "command",
    [
        ["source", "add", "https://example.invalid/paper"],
        ["feed", "add", "--type", "arxiv", "--name", "Unsafe feed", "--query", "cat:cs.AI"],
        ["skill", "create", "unsafe_skill", "--category", "reading"],
        ["project", "create", "--name", "Unsafe project"],
        [
            "agent",
            "task",
            "create",
            "--project",
            "missing",
            "--type",
            "writing",
            "--title",
            "Unsafe task",
        ],
        ["result", "list", "--project", "missing"],
        ["model", "check"],
    ],
)
def test_non_init_commands_reject_uninitialized_workspace(tmp_path, capsys, command) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "not-initialized"

    code = run([*command, "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert code == 2
    assert "Run `researchinfra init <workspace>` first" in captured.err
    assert "Traceback" not in captured.err
    assert not workspace.exists()


@pytest.mark.parametrize(
    "command",
    [
        ["source"],
        ["document"],
        ["feed"],
        ["inbox"],
        ["skill"],
        ["model"],
        ["paper"],
        ["idea"],
        ["project"],
        ["experiment"],
        ["result"],
        ["table"],
        ["figure"],
        ["claim"],
        ["draft"],
        ["agent"],
        ["agent", "task"],
    ],
)
def test_missing_subcommands_never_show_tracebacks(command, capsys) -> None:  # type: ignore[no-untyped-def]
    code = run(command)
    captured = capsys.readouterr()

    assert code == 2
    assert "usage:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "command",
    [
        ["source", "add", ""],
        ["feed", "add", "--type", "arxiv", "--name", "", "--query", "cat:cs.AI"],
        ["skill", "create", ""],
        ["skill", "create", "reader", "--category", "../../outside"],
        ["project", "create", "--name", ""],
        ["project", "create", "--name", "Missing idea", "--from-idea", "idea-missing"],
        ["figure", "create", "--project", "missing", "--title", ""],
        [
            "agent",
            "task",
            "create",
            "--project",
            "missing",
            "--type",
            "writing",
            "--title",
            "",
        ],
        [
            "agent",
            "task",
            "create",
            "--project",
            "project-missing",
            "--type",
            "writing",
            "--title",
            "Valid title",
        ],
    ],
)
def test_invalid_cli_inputs_do_not_write_files(tmp_path, capsys, command) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    before = sorted(path.relative_to(workspace) for path in workspace.rglob("*"))

    code = run([*command, "--workspace", str(workspace)])
    captured = capsys.readouterr()
    after = sorted(path.relative_to(workspace) for path in workspace.rglob("*"))

    assert code == 2
    assert "Traceback" not in captured.err
    assert before == after
    assert not (tmp_path / "outside").exists()


def test_cli_renders_pydantic_errors_without_traceback(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    project_file = workspace / "projects" / "broken" / "project.yaml"
    project_file.parent.mkdir(parents=True)
    project_file.write_text(yaml.safe_dump({"id": "project-broken", "title": ""}), encoding="utf-8")

    code = run(["project", "list", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert code == 2
    assert str(project_file) in captured.err
    assert "Malformed YAML/config file" in captured.err
    assert "restore it from git" in captured.err
    assert "Traceback" not in captured.err


def test_placeholder_default_is_honestly_rejected(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-value")
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    assert (
        run(
            [
                "source",
                "add",
                "https://example.invalid/paper",
                "--workspace",
                str(workspace),
                "--title",
                "Demo paper",
            ]
        )
        == 0
    )
    source_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in source_output.splitlines() if line.startswith("Added")
    )
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
                "anthropic",
                "--model",
                "claude-test",
            ]
        )
        == 0
    )
    capsys.readouterr()

    status_code = run(["model", "test", "--workspace", str(workspace), "--task", "reading"])
    status_output = capsys.readouterr().out
    assert status_code == 2
    assert "provider: anthropic" in status_output
    assert "can_execute: false" in status_output
    assert "secret-value" not in status_output

    before = sorted((workspace / "memory" / "readings").iterdir())
    read_code = run(["paper", "read", source_id, "--workspace", str(workspace), "--mode", "skim"])
    read_error = capsys.readouterr().err

    assert read_code == 2
    assert "`anthropic` provider is selected for `reading`" in read_error
    assert "OPENAI_API_KEY" not in read_error
    assert sorted((workspace / "memory" / "readings").iterdir()) == before


def test_model_test_requires_an_enabled_default(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()

    code = run(["model", "test", "--workspace", str(workspace), "--task", "reading"])
    output = capsys.readouterr().out

    assert code == 2
    assert "can_execute: false" in output
    assert "No enabled model default" in output
    assert "secret-value" not in output


def test_module_entry_point_works() -> None:
    repository = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "researchinfra", "--help"],
        cwd=repository,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "File-first research workspace tooling" in result.stdout
    assert "Traceback" not in result.stderr
