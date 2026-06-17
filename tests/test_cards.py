import yaml

from researchinfra.cards import IdeaCardService, PaperCardService
from researchinfra.sources import SourceRegistry


def test_paper_card_service_writes_markdown_and_yaml(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
    )

    paper_id, markdown_path, yaml_path = PaperCardService(tmp_path).create(source.id)

    assert paper_id.startswith("paper-")
    assert markdown_path.exists()
    assert yaml_path.exists()
    assert "WARNING" in markdown_path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert metadata["source_id"] == source.id


def test_idea_card_service_writes_markdown_and_yaml(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
    )
    paper_id, _, _ = PaperCardService(tmp_path).create(source.id)

    idea_id, markdown_path, yaml_path = IdeaCardService(tmp_path).generate(paper_id)

    assert idea_id.startswith("idea-")
    assert markdown_path.exists()
    assert yaml_path.exists()
    assert "WARNING" in markdown_path.read_text(encoding="utf-8")
