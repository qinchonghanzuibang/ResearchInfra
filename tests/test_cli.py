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
    assert (workspace / "memory" / "readings").exists()
    assert (workspace / "skills" / "reading" / "SKILL.md").exists()
    assert (workspace / "skills" / "reading" / "read_skim.yaml").exists()
    assert (workspace / "skills" / "writing" / "paper_card.yaml").exists()
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

    skill_code = run(["skill", "list", "--workspace", str(workspace), "--category", "writing"])
    skill_output = capsys.readouterr().out
    assert skill_code == 0
    assert "paper_card" in skill_output
    assert "\twriting\t" in skill_output

    show_code = run(["skill", "show", "paper_card", "--workspace", str(workspace)])
    show_output = capsys.readouterr().out
    assert show_code == 0
    assert "prompt_template" in show_output
    assert "required_context" in show_output

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


def test_cli_skill_create_writes_category_skill(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()

    code = run(
        [
            "skill",
            "create",
            "read_methods",
            "--workspace",
            str(workspace),
            "--category",
            "reading",
        ]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Created skill: read_methods" in output
    assert (workspace / "skills" / "reading" / "read_methods.yaml").exists()
    assert (workspace / "skills" / "reading" / "read_methods.md").exists()


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

    assert (
        run(
            [
                "model",
                "set-default",
                "--workspace",
                str(workspace),
                "--task",
                "writing",
                "--provider",
                "openai-compatible",
                "--model",
                "demo-model",
            ]
        )
        == 0
    )
    capsys.readouterr()

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


def test_cli_model_check_hides_secrets(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
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
                "demo-model",
            ]
        )
        == 0
    )
    capsys.readouterr()

    code = run(["model", "check", "--workspace", str(workspace)])
    output = capsys.readouterr().out

    assert code == 0
    assert "api_key: set" in output
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


def test_cli_source_extract_document_and_paper_prompt(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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

    assert (
        run(
            [
                "paper",
                "read",
                source_id,
                "--workspace",
                str(workspace),
                "--mode",
                "deep",
                "--dry-run",
            ]
        )
        == 0
    )
    read_prompt = capsys.readouterr().out
    assert "deep" in read_prompt
    assert "This is extracted evidence" in read_prompt
    assert "chunk-0001" in read_prompt

    assert run(["paper", "read", source_id, "--workspace", str(workspace), "--mode", "skim"]) == 0
    read_output = capsys.readouterr().out
    reading_id = next(
        line.split(": ", 1)[1]
        for line in read_output.splitlines()
        if line.startswith("Created Reading Notes")
    )
    assert (workspace / "memory" / "readings" / reading_id / "notes.md").exists()
    assert (workspace / "memory" / "readings" / reading_id / "metadata.yaml").exists()
    notes = (workspace / "memory" / "readings" / reading_id / "notes.md").read_text(
        encoding="utf-8"
    )
    assert "No model provider was configured" in notes


def test_cli_project_experiment_draft_agent_workflow(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    workspace = tmp_path / "workspace"
    assert run(["init", str(workspace)]) == 0
    capsys.readouterr()
    source_file = workspace / "sources" / "workflow-paper.md"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        "# Workflow Paper\n\nEvidence about data quality and evaluation risk.",
        encoding="utf-8",
    )

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
                "Workflow Paper",
            ]
        )
        == 0
    )
    add_output = capsys.readouterr().out
    source_id = next(
        line.split(": ", 1)[1] for line in add_output.splitlines() if line.startswith("Added")
    )
    assert run(["source", "extract", source_id, "--workspace", str(workspace)]) == 0
    capsys.readouterr()

    assert (
        run(["paper", "create-card", source_id, "--workspace", str(workspace), "--use-content"])
        == 0
    )
    paper_output = capsys.readouterr().out
    paper_id = next(
        line.split(": ", 1)[1]
        for line in paper_output.splitlines()
        if line.startswith("Created Paper Card")
    )

    assert run(["idea", "generate", "--workspace", str(workspace), "--from-paper", paper_id]) == 0
    idea_output = capsys.readouterr().out
    idea_id = next(
        line.split(": ", 1)[1]
        for line in idea_output.splitlines()
        if line.startswith("Created Idea Card")
    )

    assert run(["paper", "read", source_id, "--workspace", str(workspace), "--mode", "idea"]) == 0
    reading_output = capsys.readouterr().out
    reading_id = next(
        line.split(": ", 1)[1]
        for line in reading_output.splitlines()
        if line.startswith("Created Reading Notes")
    )

    assert (
        run(
            [
                "project",
                "create",
                "--workspace",
                str(workspace),
                "--name",
                "Grounded Workflow",
                "--from-idea",
                idea_id,
                "--from-paper",
                paper_id,
                "--from-reading",
                reading_id,
            ]
        )
        == 0
    )
    project_output = capsys.readouterr().out
    project_id = next(
        line.split(": ", 1)[1]
        for line in project_output.splitlines()
        if line.startswith("Created Project")
    )
    project_slug = project_id.removeprefix("project-")
    project_dir = workspace / "projects" / project_slug
    assert (project_dir / "project.yaml").exists()
    assert (project_dir / "context" / "project_context.md").exists()
    assert (project_dir / "experiments").exists()
    assert (project_dir / "draft").exists()
    assert (project_dir / "agents" / "tasks").exists()
    assert (project_dir / "reviews").exists()

    assert run(["project", "list", "--workspace", str(workspace)]) == 0
    assert project_id in capsys.readouterr().out

    assert run(["project", "show", project_id, "--workspace", str(workspace)]) == 0
    project_yaml = capsys.readouterr().out
    assert paper_id in project_yaml
    assert reading_id in project_yaml
    assert idea_id in project_yaml

    assert run(["project", "status", project_id, "--workspace", str(workspace)]) == 0
    assert "No experimental results" in (project_dir / "project.yaml").read_text(encoding="utf-8")
    assert "Next actions" in capsys.readouterr().out

    assert run(["project", "add-paper", project_id, paper_id, "--workspace", str(workspace)]) == 0
    assert "Linked Paper Card" in capsys.readouterr().out

    assert (
        run(["project", "add-reading", project_id, reading_id, "--workspace", str(workspace)]) == 0
    )
    assert "Linked Reading" in capsys.readouterr().out

    assert (
        run(
            [
                "experiment",
                "plan",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--dry-run",
            ]
        )
        == 0
    )
    experiment_prompt = capsys.readouterr().out
    assert "Grounded Workflow" in experiment_prompt
    assert "Do not present any proposed experiment as already run" in experiment_prompt

    assert run(["experiment", "plan", "--project", project_id, "--workspace", str(workspace)]) == 0
    capsys.readouterr()
    assert (project_dir / "experiments" / "experiment_plan.md").exists()
    assert (project_dir / "experiments" / "baseline_registry.yaml").exists()
    assert (project_dir / "experiments" / "ablation_matrix.yaml").exists()
    assert (project_dir / "experiments" / "run_registry.yaml").exists()
    assert (project_dir / "experiments" / "claim_evidence.yaml").exists()

    assert run(["experiment", "list", "--project", project_id, "--workspace", str(workspace)]) == 0
    experiment_id = capsys.readouterr().out.strip()
    assert experiment_id.startswith("experiment-")

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
                "accuracy=0.5",
            ]
        )
        == 0
    )
    assert "Added Run" in capsys.readouterr().out
    assert "accuracy" in (project_dir / "experiments" / "run_registry.yaml").read_text(
        encoding="utf-8"
    )

    assert (
        run(
            [
                "draft",
                "outline",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--venue",
                "acl",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "Do not claim results unless linked to run records" in capsys.readouterr().out

    assert (
        run(
            [
                "draft",
                "outline",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--venue",
                "acl",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (project_dir / "draft" / "outline.md").exists()

    assert (
        run(
            [
                "draft",
                "section",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--section",
                "limitations",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "missing-experiment warnings" in capsys.readouterr().out

    assert (
        run(
            [
                "draft",
                "section",
                "--project",
                project_id,
                "--workspace",
                str(workspace),
                "--section",
                "limitations",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (project_dir / "draft" / "limitations.md").exists()

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
                "Draft limitations section",
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
    assert (project_dir / "agents" / "tasks" / f"{task_id}.yaml").exists()

    assert (
        run(["agent", "task", "list", "--project", project_id, "--workspace", str(workspace)]) == 0
    )
    assert task_id in capsys.readouterr().out

    assert (
        run(
            [
                "agent",
                "task",
                "show",
                task_id,
                "--project",
                project_id,
                "--workspace",
                str(workspace),
            ]
        )
        == 0
    )
    task_yaml = capsys.readouterr().out
    assert "verification_commands" in task_yaml
    assert "Do not fabricate" in task_yaml
