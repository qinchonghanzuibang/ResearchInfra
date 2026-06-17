from researchinfra.skills import SkillRunner
from researchinfra.sources import SourceRegistry


def test_skill_runner_lists_builtin_skills(tmp_path) -> None:  # type: ignore[no-untyped-def]
    runner = SkillRunner(tmp_path)

    names = {skill.name for skill in runner.list()}

    assert {"paper_card", "idea_card", "claim_check", "experiment_plan"} <= names


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
    assert "metadata-limited" in prompt or "metadata" in prompt
    assert "Do not fabricate" in prompt
