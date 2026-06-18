"""Document content extraction and storage."""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import yaml
from pypdf import PdfReader

from researchinfra.schemas import (
    Document,
    DocumentChunk,
    DocumentSection,
    EvidenceSpan,
    Source,
    utc_now,
)
from researchinfra.sources import SourceRegistry


class DocumentError(RuntimeError):
    """Base exception for document operations."""


class DocumentNotFoundError(DocumentError):
    """Raised when a document id cannot be found."""


class DocumentStore:
    """Read extracted documents from a workspace."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.base = self.workspace / "memory" / "documents"

    def list(self) -> list[Document]:
        documents: list[Document] = []
        if not self.base.exists():
            return []
        for metadata_path in sorted(self.base.glob("*/metadata.yaml")):
            data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            documents.append(Document.model_validate(data))
        return sorted(documents, key=lambda document: document.created_at)

    def get(self, document_id: str) -> Document:
        metadata_path = self.base / document_id / "metadata.yaml"
        if not metadata_path.exists():
            raise DocumentNotFoundError(f"Document not found: {document_id}")
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        return Document.model_validate(data)

    def find_by_source_id(self, source_id: str) -> Document | None:
        for document in self.list():
            if document.source_id == source_id:
                return document
        return None

    def read_text(self, document: Document) -> str:
        path = self.workspace / document.text_path
        if not path.exists():
            raise DocumentNotFoundError(f"Document text not found: {document.text_path}")
        return path.read_text(encoding="utf-8")

    def write(self, document_id: str, text: str, metadata: dict[str, object]) -> Document:
        document_dir = self.base / document_id
        document_dir.mkdir(parents=True, exist_ok=True)
        text_path = document_dir / "text.md"
        metadata_path = document_dir / "metadata.yaml"
        metadata["text_path"] = _relative(text_path, self.workspace)
        metadata["metadata_path"] = _relative(metadata_path, self.workspace)
        text_path.write_text(text, encoding="utf-8")
        document = Document.model_validate(metadata)
        metadata_path.write_text(
            yaml.safe_dump(document.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )
        return document


class DocumentExtractor:
    """Extract source content into file-first document records."""

    def __init__(self, workspace: str | Path, *, fetch_bytes: object | None = None) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.sources = SourceRegistry(self.workspace)
        self.store = DocumentStore(self.workspace)
        self.fetch_bytes = fetch_bytes or _fetch_bytes

    def extract(self, source_id: str, *, force: bool = False) -> Document:
        existing = self.store.find_by_source_id(source_id)
        if existing is not None and not force:
            return existing

        source = self.sources.get(source_id)
        document_id = f"doc-{source.id.removeprefix('src-')}"
        result = self._extract_source(source)
        text = result.text.strip() or "No extractable text was found."
        chunks = chunk_text(text)
        sections = _sections_for_result(result, text)
        status = result.status if text != "No extractable text was found." else "failed"
        metadata = {
            "id": document_id,
            "source_id": source.id,
            "title": source.title,
            "content_type": result.content_type,
            "text_path": "",
            "metadata_path": "",
            "sections": [section.model_dump(mode="json") for section in sections],
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
            "extraction_status": status,
            "warnings": result.warnings,
            "created_at": utc_now().isoformat(),
        }
        return self.store.write(document_id, text, metadata)

    def _extract_source(self, source: Source) -> _ExtractionResult:
        if source.local is not None:
            path = self.workspace / source.local.path
            if not path.exists():
                path = Path(source.local.path)
            return self._extract_file(path)

        target = source.target
        if _is_arxiv_url(target):
            pdf_url = source.pdf_url or _arxiv_pdf_url(target)
            if pdf_url:
                try:
                    return _extract_pdf_bytes(self.fetch_bytes(pdf_url), warning_prefix=pdf_url)
                except (DocumentError, URLError, OSError) as exc:
                    return _metadata_result(
                        source,
                        warning=f"Could not download or extract arXiv PDF: {exc}",
                    )
        if source.url is not None and source.url.url:
            try:
                html = self.fetch_bytes(source.url.url).decode("utf-8", errors="replace")
            except (URLError, OSError) as exc:
                return _metadata_result(source, warning=f"Could not fetch URL content: {exc}")
            text = extract_html_text(html)
            warning = "HTML extraction is lightweight and may omit important content."
            return _ExtractionResult(
                text=text,
                content_type="html",
                status="partial",
                warnings=[warning] if text else [warning, "No readable HTML text found."],
            )
        return _metadata_result(source, warning="No extractor available for this source.")

    def _extract_file(self, path: Path) -> _ExtractionResult:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return _extract_pdf_bytes(path.read_bytes(), warning_prefix=str(path))
        if suffix in {".md", ".markdown"}:
            return _ExtractionResult(
                text=path.read_text(encoding="utf-8"),
                content_type="markdown",
                status="succeeded",
                warnings=[],
            )
        if suffix in {".txt", ".text"}:
            return _ExtractionResult(
                text=path.read_text(encoding="utf-8"),
                content_type="text",
                status="succeeded",
                warnings=[],
            )
        return _ExtractionResult(
            text="",
            content_type="unknown",
            status="failed",
            warnings=[f"No extractor available for file type: {suffix or '(none)'}"],
        )


class _ExtractionResult:
    def __init__(
        self,
        *,
        text: str,
        content_type: str,
        status: str,
        warnings: list[str],
    ) -> None:
        self.text = text
        self.content_type = content_type
        self.status = status
        self.warnings = warnings


def chunk_text(text: str, *, max_chars: int = 1200) -> list[DocumentChunk]:
    """Chunk text by paragraphs with character offsets."""

    chunks: list[DocumentChunk] = []
    current: list[str] = []
    current_start: int | None = None
    cursor = 0
    for paragraph in re.split(r"\n\s*\n", text):
        clean = paragraph.strip()
        if not clean:
            cursor += len(paragraph) + 2
            continue
        start = text.find(paragraph, cursor)
        if start == -1:
            start = cursor
        if current_start is None:
            current_start = start
        candidate = "\n\n".join([*current, clean]) if current else clean
        if current and len(candidate) > max_chars:
            chunks.append(_chunk(len(chunks), "\n\n".join(current), current_start))
            current = [clean]
            current_start = start
        else:
            current = [*current, clean]
        cursor = start + len(paragraph)
    if current and current_start is not None:
        chunks.append(_chunk(len(chunks), "\n\n".join(current), current_start))
    return chunks or [_chunk(0, text.strip() or "No extractable text was found.", 0)]


def evidence_spans(document: Document, *, limit: int = 5) -> list[EvidenceSpan]:
    """Build simple evidence spans from document chunks."""

    spans: list[EvidenceSpan] = []
    for chunk in document.chunks[:limit]:
        quote = chunk.text[:500]
        spans.append(
            EvidenceSpan(
                document_id=document.id,
                source_id=document.source_id,
                section=chunk.section,
                chunk_id=chunk.id,
                quote=quote,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
        )
    return spans


def evidence_prompt_context(document: Document, *, limit: int = 5) -> str:
    """Render extracted chunks for a model prompt."""

    lines = [
        "Extracted document evidence:",
        f"- document_id: {document.id}",
        f"- source_id: {document.source_id}",
        f"- extraction_status: {document.extraction_status}",
    ]
    if document.warnings:
        lines.append("- warnings:")
        lines.extend(f"  - {warning}" for warning in document.warnings)
    lines.append("")
    for span in evidence_spans(document, limit=limit):
        offsets = ""
        if span.start_char is not None and span.end_char is not None:
            offsets = f" chars={span.start_char}-{span.end_char}"
        lines.append(
            f"[{span.document_id}::{span.chunk_id} section={span.section or 'body'}{offsets}]"
        )
        lines.append(span.quote)
        lines.append("")
    lines.extend(
        [
            "Evidence instructions:",
            "- Cite evidence spans using document_id and chunk_id.",
            "- Do not infer claims that are not supported by the extracted text.",
            "- If extraction is partial or warnings are present, include that limitation.",
        ]
    )
    return "\n".join(lines).strip()


def extract_html_text(html: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(html)
    return "\n\n".join(parser.blocks())


def _extract_pdf_bytes(data: bytes, *, warning_prefix: str) -> _ExtractionResult:
    try:
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"# Page {index}\n\n{text.strip()}")
    except Exception as exc:  # pypdf raises several parser-specific exception types.
        raise DocumentError(f"Failed to extract PDF text from {warning_prefix}: {exc}") from exc
    warnings = []
    if not pages:
        warnings.append(f"No extractable PDF text found in {warning_prefix}.")
    return _ExtractionResult(
        text="\n\n".join(pages),
        content_type="pdf",
        status="succeeded" if pages else "failed",
        warnings=warnings,
    )


def _metadata_result(source: Source, *, warning: str) -> _ExtractionResult:
    lines = [
        f"# {source.title or source.id}",
        "",
        "Only source metadata is available.",
        "",
        f"- Source ID: {source.id}",
        f"- Target: {source.target}",
        f"- Type: {source.source_type}",
    ]
    if source.abstract:
        lines.extend(["", "## Abstract", "", source.abstract])
    return _ExtractionResult(
        text="\n".join(lines),
        content_type="metadata",
        status="partial",
        warnings=[warning, "Extraction is metadata-limited."],
    )


def _sections_for_result(result: _ExtractionResult, text: str) -> list[DocumentSection]:
    if result.content_type == "pdf":
        sections: list[DocumentSection] = []
        for match in re.finditer(r"^# Page (\d+)", text, flags=re.MULTILINE):
            sections.append(
                DocumentSection(name=f"page-{match.group(1)}", start_char=match.start())
            )
        for index, section in enumerate(sections):
            end = sections[index + 1].start_char if index + 1 < len(sections) else len(text)
            sections[index] = section.model_copy(update={"end_char": end})
        return sections or [DocumentSection(name="body", start_char=0, end_char=len(text))]
    return [DocumentSection(name="body", start_char=0, end_char=len(text))]


def _chunk(index: int, text: str, start: int) -> DocumentChunk:
    return DocumentChunk(
        id=f"chunk-{index + 1:04d}",
        section="body",
        text=text,
        start_char=start,
        end_char=start + len(text),
    )


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self._current: list[str] = []
        self._blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3"}:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._current.append(data.strip())

    def blocks(self) -> list[str]:
        self._flush()
        return self._blocks

    def _flush(self) -> None:
        if not self._current:
            return
        text = " ".join(" ".join(self._current).split())
        if text:
            self._blocks.append(text)
        self._current = []


def _fetch_bytes(url: str) -> bytes:
    try:
        with urlopen(url, timeout=30) as response:  # noqa: S310
            return response.read()
    except URLError as exc:
        raise DocumentError(f"Failed to fetch {url}: {exc.reason}") from exc


def _is_arxiv_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.netloc.lower() == "arxiv.org" and parsed.path.startswith(("/abs/", "/pdf/"))


def _arxiv_pdf_url(value: str) -> str | None:
    parsed = urlparse(value)
    path = parsed.path
    if "/abs/" in path:
        arxiv_id = path.split("/abs/", 1)[1].removesuffix(".pdf")
        return f"https://arxiv.org/pdf/{arxiv_id}"
    if "/pdf/" in path:
        arxiv_id = path.split("/pdf/", 1)[1].removesuffix(".pdf")
        return f"https://arxiv.org/pdf/{arxiv_id}"
    return None


def _relative(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace))


def document_id_for_source(source_id: str) -> str:
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:10]
    return f"doc-{digest}"
