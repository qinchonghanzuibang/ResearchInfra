"""File-first source registry for ResearchInfra workspaces."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from researchinfra.schemas import (
    Source,
    SourceLocalMetadata,
    SourceType,
    SourceUrlMetadata,
    utc_now,
)
from researchinfra.workspace_files import read_yaml_mapping, validate_yaml_records, write_yaml


class SourceRegistryError(RuntimeError):
    """Base exception for source registry operations."""


class SourceNotFoundError(SourceRegistryError):
    """Raised when a source id does not exist."""


class SourceRegistry:
    """Read and write a workspace-local source registry."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.registry_path = self.workspace / ".researchinfra" / "sources.yaml"

    def list(self) -> list[Source]:
        """Return all source records sorted by creation time."""

        data = self._read()
        sources = validate_yaml_records(
            data,
            key="sources",
            model_type=Source,
            path=self.registry_path,
        )
        return sorted(sources, key=lambda source: source.created_at)

    def get(self, source_id: str) -> Source:
        """Return a source by id."""

        for source in self.list():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Source not found: {source_id}")

    def find_by_url_or_external_id(
        self, *, url: str | None = None, external_id: str | None = None
    ) -> Source | None:
        """Find a source by normalized URL or external id."""

        normalized_url = _normalize_url(url) if url else None
        for source in self.list():
            source_url = source.url.url if source.url is not None else source.target
            if normalized_url and _normalize_url(source_url) == normalized_url:
                return source
            if external_id and source.external_id == external_id:
                return source
        return None

    def add(
        self,
        target: str,
        *,
        source_type: SourceType = "unknown",
        title: str | None = None,
        tags: list[str] | None = None,
        abstract: str | None = None,
        authors: list[str] | None = None,
        published_at: object | None = None,
        external_id: str | None = None,
        pdf_url: str | None = None,
        bibtex: str | None = None,
        raw_metadata: dict[str, object] | None = None,
    ) -> Source:
        """Add or update a source record for a local path or URL."""

        target = target.strip()
        if not target:
            raise SourceRegistryError("Source target must not be empty.")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_target = self._normalize_target(target)
        source_id = self._source_id(normalized_target)
        sources = self.list()
        existing = next((source for source in sources if source.id == source_id), None)
        now = utc_now()

        if existing is None:
            source = self._build_source(
                source_id,
                normalized_target,
                source_type=source_type,
                title=title,
                tags=tags or [],
                abstract=abstract,
                authors=authors or [],
                published_at=published_at,
                external_id=external_id,
                pdf_url=pdf_url,
                bibtex=bibtex,
                raw_metadata=raw_metadata or {},
                created_at=now,
                updated_at=now,
            )
            sources.append(source)
        else:
            source = existing.model_copy(
                update={
                    "source_type": source_type,
                    "title": title or existing.title,
                    "abstract": abstract or existing.abstract,
                    "authors": authors if authors is not None else existing.authors,
                    "published_at": published_at or existing.published_at,
                    "external_id": external_id or existing.external_id,
                    "pdf_url": pdf_url or existing.pdf_url,
                    "bibtex": bibtex or existing.bibtex,
                    "tags": tags if tags is not None else existing.tags,
                    "raw_metadata": (
                        raw_metadata if raw_metadata is not None else existing.raw_metadata
                    ),
                    "updated_at": now,
                }
            )
            sources = [source if item.id == source_id else item for item in sources]

        self._write(sources)
        return source

    def _build_source(
        self,
        source_id: str,
        target: str,
        *,
        source_type: SourceType,
        title: str | None,
        tags: list[str],
        abstract: str | None,
        authors: list[str],
        published_at: object | None,
        external_id: str | None,
        pdf_url: str | None,
        bibtex: str | None,
        raw_metadata: dict[str, object],
        created_at: datetime,
        updated_at: datetime,
    ) -> Source:
        if _is_url(target):
            parsed = urlparse(target)
            return Source(
                id=source_id,
                source_type=source_type,
                target=target,
                title=title,
                abstract=abstract,
                authors=authors,
                published_at=published_at,
                external_id=external_id,
                pdf_url=pdf_url,
                bibtex=bibtex,
                tags=tags,
                url=SourceUrlMetadata(url=target, domain=parsed.netloc or None),
                raw_metadata=raw_metadata,
                created_at=created_at,
                updated_at=updated_at,
            )

        path = Path(target).expanduser()
        if not path.is_absolute():
            path = (self.workspace / path).resolve()
        stat = path.stat() if path.exists() else None
        created = (
            datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc) if stat is not None else None
        )
        display_path = _human_path(path, self.workspace)
        return Source(
            id=source_id,
            source_type=source_type,
            target=display_path,
            title=title,
            abstract=abstract,
            authors=authors,
            published_at=published_at,
            external_id=external_id,
            pdf_url=pdf_url,
            bibtex=bibtex,
            tags=tags,
            local=SourceLocalMetadata(
                path=display_path,
                filename=path.name,
                extension=path.suffix.lstrip(".") or None,
                size_bytes=stat.st_size if stat is not None else None,
                created_at=created,
            ),
            raw_metadata=raw_metadata,
            created_at=created_at,
            updated_at=updated_at,
        )

    def update(self, source: Source) -> Source:
        """Replace an existing source record."""

        sources = self.list()
        if not any(item.id == source.id for item in sources):
            raise SourceNotFoundError(f"Source not found: {source.id}")
        updated = source.model_copy(update={"updated_at": utc_now()})
        self._write([updated if item.id == updated.id else item for item in sources])
        return updated

    def _read(self) -> dict[str, object]:
        if not self.registry_path.exists():
            return {"sources": []}
        return read_yaml_mapping(self.registry_path)

    def _write(self, sources: list[Source]) -> None:
        data = {"sources": [source.model_dump(mode="json") for source in sources]}
        write_yaml(self.registry_path, data)

    def _normalize_target(self, target: str) -> str:
        if _is_url(target):
            return target.strip()
        path = Path(target).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return _human_path(path, self.workspace)

    @staticmethod
    def _source_id(target: str) -> str:
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()[:10]
        return f"src-{digest}"


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_url(value: str) -> str:
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"


def _human_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace))
    except ValueError:
        return str(path.resolve())
