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


def test_cli_feed_inbox_and_enrich_workflow(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    feed_xml = tmp_path / "feed.xml"
    feed_xml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><item>
        <title>RSS Research Note</title>
        <link>https://example.com/research-note</link>
        <description>Short summary.</description>
        <guid>rss-note-1</guid>
        </item></channel></rss>
        """,
        encoding="utf-8",
    )

    assert (
        run(
            [
                "feed",
                "add",
                "--workspace",
                str(workspace),
                "--type",
                "rss",
                "--name",
                "RSS",
                "--url",
                feed_xml.as_uri(),
            ]
        )
        == 0
    )
    feed_output = capsys.readouterr().out
    feed_id = next(
        line.split(": ", 1)[1] for line in feed_output.splitlines() if line.startswith("Added")
    )

    assert run(["feed", "list", "--workspace", str(workspace)]) == 0
    assert feed_id in capsys.readouterr().out

    assert run(["feed", "sync", "--workspace", str(workspace), "--limit", "5"]) == 0
    sync_output = capsys.readouterr().out
    item_id = next(
        line.split("\t", 1)[0] for line in sync_output.splitlines() if line.startswith("inbox-")
    )

    assert run(["inbox", "list", "--workspace", str(workspace)]) == 0
    assert "RSS Research Note" in capsys.readouterr().out

    assert run(["inbox", "show", item_id, "--workspace", str(workspace)]) == 0
    assert "rss-note-1" in capsys.readouterr().out

    assert run(["inbox", "promote", item_id, "--workspace", str(workspace)]) == 0
    promote_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in promote_output.splitlines() if line.startswith("Source")
    )

    assert run(["source", "enrich", source_id, "--workspace", str(workspace)]) == 0
    assert "Enriched source" in capsys.readouterr().out

    assert run(["inbox", "skip", item_id, "--workspace", str(workspace)]) == 0
    assert "Skipped inbox item" in capsys.readouterr().out


def test_cli_source_extract_document_and_paper_prompt(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    source_file = workspace / "sources" / "paper.md"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("# Demo\n\nThis is extracted evidence.", encoding="utf-8")

    assert (
        run(
            [
                "source",
                "add",
                str(source_file),
                "--workspace",
                str(workspace),
                "--type",
                "paper",
                "--title",
                "Demo",
            ]
        )
        == 0
    )
    add_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in add_output.splitlines() if line.startswith("Added")
    )

    assert run(["source", "extract", source_id, "--workspace", str(workspace)]) == 0
    extract_output = capsys.readouterr().out
    document_id = next(
        line.split(": ", 1)[1]
        for line in extract_output.splitlines()
        if line.startswith("Extracted document")
    )

    assert run(["document", "list", "--workspace", str(workspace)]) == 0
    assert document_id in capsys.readouterr().out

    assert run(["document", "show", document_id, "--workspace", str(workspace)]) == 0
    assert "This is extracted evidence" in capsys.readouterr().out

    assert (
        run(["document", "chunks", document_id, "--workspace", str(workspace), "--limit", "1"]) == 0
    )
    assert "chunk-0001" in capsys.readouterr().out

    assert (
        run(
            [
                "paper",
                "create-card",
                source_id,
                "--workspace",
                str(workspace),
                "--use-content",
                "--dry-run",
            ]
        )
        == 0
    )
    prompt = capsys.readouterr().out
    assert "Extracted document evidence" in prompt
    assert "chunk-0001" in prompt
    assert "Do not infer claims" in prompt
