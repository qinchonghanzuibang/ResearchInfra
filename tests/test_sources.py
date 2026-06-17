import yaml

from researchinfra.sources import SourceRegistry


def test_source_registry_adds_url_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    registry = SourceRegistry(workspace)

    source = registry.add(
        "https://arxiv.org/abs/1234.5678",
        source_type="paper",
        title="Demo Paper",
        tags=["demo", "arxiv"],
    )

    assert source.id.startswith("src-")
    assert source.url is not None
    assert source.url.domain == "arxiv.org"
    assert source.source_type == "paper"
    assert source.title == "Demo Paper"
    assert (workspace / ".researchinfra" / "sources.yaml").exists()

    data = yaml.safe_load((workspace / ".researchinfra" / "sources.yaml").read_text())
    assert data["sources"][0]["id"] == source.id


def test_source_registry_adds_local_file_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace"
    source_file = workspace / "sources" / "note.md"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("# Note\n", encoding="utf-8")
    registry = SourceRegistry(workspace)

    source = registry.add(str(source_file), source_type="note", title="Local Note")

    assert source.local is not None
    assert source.local.filename == "note.md"
    assert source.local.extension == "md"
    assert source.local.size_bytes == len("# Note\n")
    assert source.local.path == "sources/note.md"
