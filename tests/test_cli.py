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
