import pytest
from pydantic import ValidationError

from researchinfra.schemas import (
    Ablation,
    AgentBackendConfig,
    AgentTask,
    Baseline,
    Claim,
    ClaimEvidenceLink,
    Document,
    DocumentChunk,
    DocumentSection,
    Draft,
    EvidenceLink,
    EvidenceSpan,
    Experiment,
    ExperimentPlan,
    Feed,
    Idea,
    InboxItem,
    ModelProviderConfig,
    Paper,
    Project,
    ResultRecord,
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
    baseline = Baseline(id="baseline:example", name="Current baseline")
    ablation = Ablation(id="ablation:example", factor="data_quality", levels=["low", "high"])
    experiment_plan = ExperimentPlan(
        id="experiment-plan:example",
        project_id=project.id,
        title="Plan",
        baselines=[baseline],
        ablations=[ablation],
    )
    run = Run(id="run:example", experiment_id=experiment.id, metrics={"status": "not_run"})
    result = ResultRecord(
        id="result:example",
        experiment_id=experiment.id,
        metrics={"accuracy": 0.5},
    )
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
    document = Document(
        id="doc:example",
        source_id=source.id,
        title="Document",
        content_type="text",
        text_path="memory/documents/doc/text.md",
        metadata_path="memory/documents/doc/metadata.yaml",
        sections=[DocumentSection(name="body", start_char=0, end_char=10)],
        chunks=[DocumentChunk(id="chunk-0001", text="Evidence text", start_char=0, end_char=13)],
        extraction_status="succeeded",
    )
    evidence_span = EvidenceSpan(
        document_id=document.id,
        source_id=source.id,
        section="body",
        chunk_id="chunk-0001",
        quote="Evidence text",
    )
    claim_evidence = ClaimEvidenceLink(
        claim_id=claim.id,
        evidence=[EvidenceLink(kind="run", ref=run.id)],
        status="partial",
    )
    agent_task = AgentTask(
        id="task:example",
        title="Draft section",
        task_type="writing",
        project_id=project.id,
        backend="manual",
        context_files=["projects/demo/project.yaml"],
        expected_outputs=["draft"],
        constraints=["Do not fabricate results."],
        verification_commands=["python -m pytest"],
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
    assert project.research_question is None
    assert experiment_plan.baselines[0].name == "Current baseline"
    assert experiment_plan.ablations[0].factor == "data_quality"
    assert run.metrics["status"] == "not_run"
    assert result.metrics["accuracy"] == 0.5
    assert draft.status == "outline"
    assert review.decision == "no_decision"
    assert source.source_type == "web"
    assert feed.type == "arxiv"
    assert inbox_item.status == "new"
    assert document.chunks[0].id == "chunk-0001"
    assert evidence_span.quote == "Evidence text"
    assert claim_evidence.status == "partial"
    assert agent_task.task_type == "writing"
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
