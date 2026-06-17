import pytest
from pydantic import ValidationError

from researchinfra.schemas import (
    AgentBackendConfig,
    Claim,
    Draft,
    EvidenceLink,
    Experiment,
    Feed,
    Idea,
    InboxItem,
    ModelProviderConfig,
    Paper,
    Project,
    Review,
    Run,
    Skill,
    Source,
    WorkspaceConfig,
)


def test_core_schemas_validate_minimal_objects() -> None:
    paper = Paper(id="paper:example", title="A Real Paper")
    claim = Claim(
        id="claim:example",
        text="The claim remains a hypothesis until evidence is linked.",
        evidence=[EvidenceLink(kind="paper", ref=paper.id)],
    )
    idea = Idea(id="idea:example", title="Evidence map", related_papers=[paper.id])
    project = Project(id="project:example", title="Evidence-grounded drafting")
    experiment = Experiment(
        id="experiment:example",
        project_id=project.id,
        title="Evaluate evidence mapping workflow",
    )
    run = Run(id="run:example", experiment_id=experiment.id, metrics={"status": "not_run"})
    draft = Draft(id="draft:example", title="Draft", claims=[claim.id])
    review = Review(id="review:example", reviewer="human")
    source = Source(id="source:example", target="https://example.com", source_type="web")
    feed = Feed(id="feed:example", name="arXiv", type="arxiv", query="cat:cs.CL")
    inbox_item = InboxItem(
        id="inbox:example",
        feed_id=feed.id,
        type="paper",
        title="Inbox Paper",
        url="https://arxiv.org/abs/1234.5678",
    )
    skill = Skill(
        name="paper_card",
        description="Create a Paper Card.",
        prompt_template="Read $input_text",
    )
    provider = ModelProviderConfig(id="ollama-local", provider="ollama")
    backend = AgentBackendConfig(id="manual", backend="manual", enabled=True)
    workspace = WorkspaceConfig(
        name="lab",
        model_providers=[provider],
        agent_backends=[backend],
    )

    assert claim.evidence[0].ref == paper.id
    assert idea.status == "seed"
    assert run.metrics["status"] == "not_run"
    assert draft.status == "outline"
    assert review.decision == "no_decision"
    assert source.source_type == "web"
    assert feed.type == "arxiv"
    assert inbox_item.status == "new"
    assert skill.name == "paper_card"
    assert workspace.schema_version == "0.1"


def test_schemas_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Paper(id="paper:example", title="A Real Paper", fabricated_score=99)  # type: ignore[call-arg]


def test_provider_and_backend_kinds_are_constrained() -> None:
    with pytest.raises(ValidationError):
        ModelProviderConfig(id="bad", provider="unknown")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        AgentBackendConfig(id="bad", backend="unknown")  # type: ignore[arg-type]
