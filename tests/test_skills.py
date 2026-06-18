import yaml

from researchinfra.skills import SkillRunner
from researchinfra.sources import SourceRegistry


def test_skill_runner_lists_builtin_skills(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runner = SkillRunner(tmp_path)

    names = {skill.name for skill in runner.list()}

    assert {"paper_card", "idea_card", "claim_check", "experiment_plan"} <= names
    assert {"read_skim", "read_deep", "read_related_work"} <= names
    assert {skill.name for skill in runner.list(category="reading")} >= {"read_skim"}


def test_skill_runner_renders_source_prompt(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registry = SourceRegistry(tmp_path)
    source = registry.add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
    )
    runner = SkillRunner(tmp_path)

    prompt = runner.render("paper_card", source.id)

    assert "Demo Paper" in prompt
    assert "Metadata:" in prompt
    assert "Do not fabricate" in prompt


def test_skill_runner_loads_workspace_category_skill(tmp_path) -> None:  # type: ignore[no-untyped-def]
    skill_dir = tmp_path / "skills" / "reading"
    skill_dir.mkdir(parents=True)
    (skill_dir / "custom_read.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "custom_read",
                "category": "reading",
                "description": "Read with local lab conventions.",
                "input_type": "source",
                "output_type": "markdown",
                "required_context": ["source", "warnings"],
                "prompt_template": "custom_read.md",
                "recommended_model": "optional",
                "version": "0.1",
                "tags": ["local"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (skill_dir / "custom_read.md").write_text(
        "Title: $title\nWarnings: $warnings\n",
        encoding="utf-8",
    )
    source = SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
    )

    runner = SkillRunner(tmp_path)
    skill = runner.get("custom_read")
    prompt = runner.render("custom_read", source.id)

    assert skill.origin == "workspace"
    assert skill.category == "reading"
    assert "Demo Paper" in prompt
    assert "No extracted document content" in prompt


def test_workspace_skill_overrides_builtin(tmp_path) -> None:  # type: ignore[no-untyped-def]
    skill_dir = tmp_path / "skills" / "writing"
    skill_dir.mkdir(parents=True)
    (skill_dir / "paper_card.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "paper_card",
                "category": "writing",
                "description": "Local Paper Card override.",
                "prompt_template": "paper_card.md",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (skill_dir / "paper_card.md").write_text("LOCAL OVERRIDE: $title\n", encoding="utf-8")
    source = SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
    )

    runner = SkillRunner(tmp_path)

    assert runner.get("paper_card").origin == "workspace"
    assert runner.render("paper_card", source.id).strip() == "LOCAL OVERRIDE: Demo Paper"


def test_skill_runner_create_writes_yaml_and_prompt(tmp_path) -> None:  # type: ignore[no-untyped-def]
    yaml_path, prompt_path = SkillRunner(tmp_path).create("triage", category="reading")

    assert yaml_path == tmp_path / "skills" / "reading" / "triage.yaml"
    assert prompt_path == tmp_path / "skills" / "reading" / "triage.md"
    assert "prompt_template: triage.md" in yaml_path.read_text(encoding="utf-8")
    assert "$chunks" in prompt_path.read_text(encoding="utf-8")
