"""File-first source registry for ResearchInfra workspaces."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

from researchinfra.schemas import (
    Source,
    SourceLocalMetadata,
    SourceType,
    SourceUrlMetadata,
    utc_now,
)


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
        sources = [Source.model_validate(item) for item in data.get("sources", [])]
        return sorted(sources, key=lambda source: source.created_at)

    def get(self, source_id: str) -> Source:
        """Return a source by id."""

        for source in self.list():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Source not found: {source_id}")

    def add(
        self,
        target: str,
        *,
        source_type: SourceType = "unknown",
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> Source:
        """Add or update a source record for a local path or URL."""

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
                created_at=now,
                updated_at=now,
            )
            sources.append(source)
        else:
            source = existing.model_copy(
                update={
                    "source_type": source_type,
                    "title": title or existing.title,
                    "tags": tags if tags is not None else existing.tags,
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
                tags=tags,
                url=SourceUrlMetadata(url=target, domain=parsed.netloc or None),
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
            tags=tags,
            local=SourceLocalMetadata(
                path=display_path,
                filename=path.name,
                extension=path.suffix.lstrip(".") or None,
                size_bytes=stat.st_size if stat is not None else None,
                created_at=created,
            ),
            created_at=created_at,
            updated_at=updated_at,
        )

    def _read(self) -> dict[str, object]:
        if not self.registry_path.exists():
            return {"sources": []}
        data = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise SourceRegistryError(f"Invalid source registry: {self.registry_path}")
        return data

    def _write(self, sources: list[Source]) -> None:
        data = {"sources": [source.model_dump(mode="json") for source in sources]}
        self.registry_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

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


def _human_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace))
    except ValueError:
        return str(path.resolve())
