from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from researchinfra.documents import (
    DocumentExtractor,
    DocumentStore,
    chunk_text,
    evidence_prompt_context,
    evidence_spans,
)
from researchinfra.sources import SourceRegistry


def test_text_extraction_stores_document_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source_file = tmp_path / "paper.md"
    source_file.write_text("# Demo Paper\n\nThis paragraph is evidence.\n", encoding="utf-8")
    source = SourceRegistry(tmp_path).add(str(source_file), source_type="paper", title="Demo")

    document = DocumentExtractor(tmp_path).extract(source.id)

    assert document.id.startswith("doc-")
    assert document.content_type == "markdown"
    assert document.extraction_status == "succeeded"
    assert document.chunks
    assert (tmp_path / document.text_path).exists()
    assert (tmp_path / document.metadata_path).exists()
    assert "This paragraph is evidence" in (tmp_path / document.text_path).read_text()


def test_pdf_extraction_reads_small_pdf_fixture(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pdf_path = tmp_path / "paper.pdf"
    _write_pdf(pdf_path, "Hello PDF evidence")
    source = SourceRegistry(tmp_path).add(str(pdf_path), source_type="paper", title="PDF")

    document = DocumentExtractor(tmp_path).extract(source.id)

    assert document.content_type == "pdf"
    assert document.extraction_status == "succeeded"
    assert "Hello PDF evidence" in (tmp_path / document.text_path).read_text()


def test_chunking_and_evidence_spans_are_serializable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source_file = tmp_path / "note.txt"
    source_file.write_text(
        "First evidence paragraph.\n\nSecond evidence paragraph.", encoding="utf-8"
    )
    source = SourceRegistry(tmp_path).add(str(source_file), source_type="note", title="Note")
    document = DocumentExtractor(tmp_path).extract(source.id)

    chunks = chunk_text("Alpha paragraph.\n\nBeta paragraph.", max_chars=20)
    spans = evidence_spans(document)

    assert len(chunks) == 2
    assert spans[0].document_id == document.id
    assert spans[0].source_id == source.id
    assert "Evidence instructions" in evidence_prompt_context(document)


def test_document_store_lists_and_reads_documents(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source_file = tmp_path / "paper.txt"
    source_file.write_text("Stored evidence.", encoding="utf-8")
    source = SourceRegistry(tmp_path).add(str(source_file), source_type="paper", title="Stored")
    document = DocumentExtractor(tmp_path).extract(source.id)
    store = DocumentStore(tmp_path)

    assert store.get(document.id).id == document.id
    assert store.find_by_source_id(source.id) is not None
    assert "Stored evidence" in store.read_text(document)
    assert [item.id for item in store.list()] == [document.id]


def _write_pdf(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/F1"): DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
        }
    )
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): font})
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 200 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = stream
    with path.open("wb") as output:
        writer.write(output)
