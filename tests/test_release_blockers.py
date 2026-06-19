"""Regression tests for public-release security and workspace safety blockers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

from researchinfra.cli import run
from researchinfra.models.adapters import OpenAICompatibleProvider, redact_sensitive_text
from researchinfra.models.base import ModelProviderRequestError
from researchinfra.schemas import ModelProviderConfig


def test_provider_errors_and_status_never_expose_secrets(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sentinel = "release-sentinel-openai-key"
    secrets = {
        "OPENAI_API_KEY": sentinel,
        "ANTHROPIC_API_KEY": "release-sentinel-anthropic-key",
        "OPENROUTER_API_KEY": "release-sentinel-openrouter-key",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("OPENAI_BASE_URL", f"https://example.invalid/v1?api_key={sentinel}")

    body = (
        "Authorization: Bearer header-token Bearer bearer-token "
        '{"api_key":"json-key","token":"token-value","access_token":"access-value",'
        '"secret":"secret-value","authorization":"Bearer json-bearer"} '
        f"configured={secrets['OPENAI_API_KEY']} "
        f"configured={secrets['ANTHROPIC_API_KEY']} "
        f"configured={secrets['OPENROUTER_API_KEY']}"
    )

    def fail_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise HTTPError(
            "https://example.invalid/v1/chat/completions",
            401,
            "Unauthorized",
            None,
            BytesIO(body.encode("utf-8")),
        )

    monkeypatch.setattr("researchinfra.models.adapters.urlopen", fail_request)
    provider = OpenAICompatibleProvider(
        ModelProviderConfig(id="openai-compatible", provider="openai-compatible")
    )

    with pytest.raises(ModelProviderRequestError) as error:
        provider.complete("hello")

    message = str(error.value)
    for secret in (
        *secrets.values(),
        "header-token",
        "bearer-token",
        "json-key",
        "token-value",
        "access-value",
        "secret-value",
        "json-bearer",
    ):
        assert secret not in message
    assert "HTTP 401" in message
    assert sentinel not in str(provider.status()["base_url"])

    redacted = redact_sensitive_text(body)
    for secret in (
        *secrets.values(),
        "header-token",
        "bearer-token",
        "json-key",
        "token-value",
        "access-value",
        "secret-value",
        "json-bearer",
    ):
        assert secret not in redacted


def test_cli_provider_failure_never_prints_sentinel_key(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sentinel = "cli-release-sentinel-key"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("OPENAI_API_KEY", sentinel)

    def fail_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise HTTPError(
            "https://example.invalid/v1/chat/completions",
            401,
            "Unauthorized",
            None,
            BytesIO(f"Authorization: Bearer {sentinel}".encode()),
        )

    monkeypatch.setattr("researchinfra.models.adapters.urlopen", fail_request)
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
            ]
        )
        == 0
    )
    source_id = _created_id(capsys.readouterr().out, "Added source")
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
                "demo-model",
            ]
        )
        == 0
    )
    capsys.readouterr()

    code = run(["paper", "read", source_id, "--workspace", str(workspace), "--mode", "skim"])
    captured = capsys.readouterr()

    assert code == 2
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    assert "Traceback" not in captured.err


def test_force_only_adds_missing_files_and_reinitialize_requires_confirmation(
    tmp_path, capsys
) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
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
                "preserve-me",
            ]
        )
        == 0
    )
    capsys.readouterr()

    config_path = workspace / ".researchinfra" / "workspace.yaml"
    backend_path = workspace / "agents" / "backends" / "manual.yaml"
    guide_path = workspace / "docs" / "README.md"
    skill_path = workspace / "skills" / "reading" / "read_skim.yaml"
    config_before = config_path.read_text(encoding="utf-8")
    backend_path.write_text("user: configured\n", encoding="utf-8")
    skill_path.write_text("user: customized\n", encoding="utf-8")
    guide_path.unlink()

    assert run(["init", str(workspace), "--force"]) == 0
    output = capsys.readouterr().out

    assert "Preserved config" in output
    assert config_path.read_text(encoding="utf-8") == config_before
    assert backend_path.read_text(encoding="utf-8") == "user: configured\n"
    assert skill_path.read_text(encoding="utf-8") == "user: customized\n"
    assert guide_path.exists()

    assert run(["init", str(workspace), "--reinitialize"]) == 2
    captured = capsys.readouterr()
    assert "requires `--yes`" in captured.err
    assert "preserve-me" in config_path.read_text(encoding="utf-8")

    assert run(["init", str(workspace), "--reinitialize", "--yes"]) == 0
    assert "model_defaults: {}" in config_path.read_text(encoding="utf-8")
    assert "user: configured" not in backend_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("relative_path", "command"),
    [
        (".researchinfra/workspace.yaml", ["model", "list"]),
        (".researchinfra/sources.yaml", ["source", "list"]),
        (".researchinfra/feeds.yaml", ["feed", "list"]),
        (".researchinfra/inbox.yaml", ["inbox", "list"]),
        ("skills/reading/read_skim.yaml", ["skill", "list"]),
    ],
)
def test_malformed_workspace_registry_yaml_fails_cleanly_without_writes(
    tmp_path, capsys, relative_path, command
) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    target = workspace / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("broken: [\n", encoding="utf-8")
    before = _workspace_files(workspace)

    code = run([*command, "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert code == 2
    assert str(target) in captured.err
    assert "Malformed YAML/config file" in captured.err
    assert "restore it from git" in captured.err
    assert "Traceback" not in captured.err
    assert _workspace_files(workspace) == before


@pytest.mark.parametrize(
    ("relative_path", "command", "needs_project"),
    [
        ("project.yaml", ["project", "list"], False),
        ("experiments/run_registry.yaml", ["result", "list"], True),
        ("claims/claim_evidence.yaml", ["claim", "list"], True),
        ("agents/tasks/task-writing-0001.yaml", ["agent", "task", "list"], True),
        ("results/metrics.yaml", ["paper", "check", "--venue", "arxiv"], True),
        ("paper/arxiv/metadata.yaml", ["paper", "check", "--venue", "arxiv"], True),
    ],
)
def test_malformed_project_registry_yaml_fails_cleanly_without_writes(
    tmp_path, capsys, relative_path, command, needs_project
) -> None:  # type: ignore[no-untyped-def]
    workspace, project_id, project_dir = _workspace_with_project(tmp_path, capsys)
    target = project_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("broken: [\n", encoding="utf-8")
    before = _workspace_files(workspace)

    project_args = ["--project", project_id] if needs_project else []
    code = run([*command, *project_args, "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert code == 2
    assert str(target) in captured.err
    assert "Malformed YAML/config file" in captured.err
    assert "Traceback" not in captured.err
    assert _workspace_files(workspace) == before


def test_schema_invalid_yaml_record_has_a_recovery_message(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    target = workspace / ".researchinfra" / "sources.yaml"
    target.write_text("sources:\n  - id: ''\n", encoding="utf-8")
    before = _workspace_files(workspace)

    code = run(["source", "list", "--workspace", str(workspace)])
    captured = capsys.readouterr()

    assert code == 2
    assert str(target) in captured.err
    assert "Malformed YAML/config file" in captured.err
    assert "fix its yaml syntax" in captured.err.lower()
    assert "Traceback" not in captured.err
    assert _workspace_files(workspace) == before


def _workspace_with_project(tmp_path, capsys) -> tuple[Path, str, Path]:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    assert run(["project", "create", "--workspace", str(workspace), "--name", "Registry Demo"]) == 0
    project_id = _created_id(capsys.readouterr().out, "Created Project")
    project_dir = workspace / "projects" / project_id.removeprefix("project-")
    assert run(["experiment", "plan", "--project", project_id, "--workspace", str(workspace)]) == 0
    capsys.readouterr()
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
                "Check registry safety",
            ]
        )
        == 0
    )
    capsys.readouterr()
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
    capsys.readouterr()
    assert run(["result", "list", "--project", project_id, "--workspace", str(workspace)]) == 0
    capsys.readouterr()
    return workspace, project_id, project_dir


def _workspace_files(workspace: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(workspace): path.read_bytes()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


def _created_id(output: str, prefix: str) -> str:
    return next(line.split(": ", 1)[1] for line in output.splitlines() if line.startswith(prefix))
