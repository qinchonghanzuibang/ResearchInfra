from researchinfra.cli import run


def test_cli_help(capsys) -> None:  # type: ignore[no-untyped-def]
    exit_code = run(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "researchinfra" in captured.out
    assert "init" in captured.out


def test_cli_init_creates_workspace(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "my-research"

    exit_code = run(["init", str(workspace)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Initialized ResearchInfra workspace" in captured.out
    assert (workspace / ".researchinfra" / "workspace.yaml").exists()
    assert (workspace / "skills" / "reading" / "SKILL.md").exists()
    assert (workspace / "templates" / "venues" / "neurips" / "main.tex").exists()


def test_cli_source_and_skill_dry_run(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()

    add_code = run(
        [
            "source",
            "add",
            "https://arxiv.org/abs/1234.5678",
            "--workspace",
            str(workspace),
            "--type",
            "paper",
            "--title",
            "Demo Paper",
        ]
    )
    add_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in add_output.splitlines() if line.startswith("Added")
    )
    assert add_code == 0

    list_code = run(["source", "list", "--workspace", str(workspace)])
    list_output = capsys.readouterr().out
    assert list_code == 0
    assert source_id in list_output
    assert "Demo Paper" in list_output

    skill_code = run(["skill", "list", "--workspace", str(workspace)])
    skill_output = capsys.readouterr().out
    assert skill_code == 0
    assert "paper_card" in skill_output

    dry_run_code = run(
        [
            "skill",
            "run",
            "paper_card",
            "--workspace",
            str(workspace),
            "--input",
            source_id,
            "--dry-run",
        ]
    )
    dry_run_output = capsys.readouterr().out
    assert dry_run_code == 0
    assert "Demo Paper" in dry_run_output
    assert "Do not fabricate" in dry_run_output


def test_cli_skill_missing_api_key_is_clear(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    assert (
        run(
            [
                "source",
                "add",
                "https://arxiv.org/abs/1234.5678",
                "--workspace",
                str(workspace),
                "--type",
                "paper",
                "--title",
                "Demo Paper",
            ]
        )
        == 0
    )
    add_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in add_output.splitlines() if line.startswith("Added")
    )

    code = run(
        [
            "skill",
            "run",
            "paper_card",
            "--workspace",
            str(workspace),
            "--input",
            source_id,
        ]
    )
    captured = capsys.readouterr()

    assert code == 2
    assert "OPENAI_API_KEY is not set" in captured.err
    assert "Traceback" not in captured.err


def test_cli_model_check_hides_secrets(capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")

    code = run(["model", "check"])
    output = capsys.readouterr().out

    assert code == 0
    assert "API key: set" in output
    assert "secret-value" not in output
    assert "demo-model" in output


def test_cli_creates_paper_and_idea_cards(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    assert (
        run(
            [
                "source",
                "add",
                "https://arxiv.org/abs/1234.5678",
                "--workspace",
                str(workspace),
                "--type",
                "paper",
                "--title",
                "Demo Paper",
            ]
        )
        == 0
    )
    add_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in add_output.splitlines() if line.startswith("Added")
    )

    paper_code = run(["paper", "create-card", source_id, "--workspace", str(workspace)])
    paper_output = capsys.readouterr().out
    paper_id = next(
        line.split(": ", 1)[1]
        for line in paper_output.splitlines()
        if line.startswith("Created Paper Card")
    )
    assert paper_code == 0
    assert (workspace / "memory" / "papers" / f"{paper_id}.md").exists()
    assert (workspace / "memory" / "papers" / f"{paper_id}.yaml").exists()

    idea_code = run(["idea", "generate", "--workspace", str(workspace), "--from-paper", paper_id])
    idea_output = capsys.readouterr().out
    idea_id = next(
        line.split(": ", 1)[1]
        for line in idea_output.splitlines()
        if line.startswith("Created Idea Card")
    )
    assert idea_code == 0
    assert (workspace / "memory" / "ideas" / f"{idea_id}.md").exists()
    assert (workspace / "memory" / "ideas" / f"{idea_id}.yaml").exists()
