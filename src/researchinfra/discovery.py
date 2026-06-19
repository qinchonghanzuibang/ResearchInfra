"""Feed discovery, inbox review, and source enrichment."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus, urlparse
from urllib.request import urlopen

import yaml

from researchinfra.schemas import Feed, FeedType, InboxItem, InboxStatus, Source, utc_now
from researchinfra.sources import SourceRegistry


class DiscoveryError(RuntimeError):
    """Base exception for feed and inbox operations."""


class FeedNotFoundError(DiscoveryError):
    """Raised when a feed id does not exist."""


class InboxItemNotFoundError(DiscoveryError):
    """Raised when an inbox item id does not exist."""


FetchText = Callable[[str], str]


class FeedRegistry:
    """Read and write configured discovery feeds."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.path = self.workspace / ".researchinfra" / "feeds.yaml"

    def list(self) -> list[Feed]:
        data = self._read()
        feeds = [Feed.model_validate(item) for item in data.get("feeds", [])]
        return sorted(feeds, key=lambda feed: feed.created_at)

    def get(self, feed_id: str) -> Feed:
        for feed in self.list():
            if feed.id == feed_id:
                return feed
        raise FeedNotFoundError(f"Feed not found: {feed_id}")

    def add(
        self,
        *,
        name: str,
        feed_type: FeedType,
        url: str | None = None,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> Feed:
        name = name.strip()
        if not name:
            raise DiscoveryError("Feed name must not be empty.")
        if feed_type == "arxiv" and not query:
            raise DiscoveryError("arxiv feeds require --query")
        if feed_type in {"rss", "atom", "web"} and not url:
            raise DiscoveryError(f"{feed_type} feeds require --url")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        feed_id = _stable_id("feed", feed_type, name, query or url or "")
        feeds = self.list()
        existing = next((feed for feed in feeds if feed.id == feed_id), None)
        if existing is None:
            feed = Feed(
                id=feed_id,
                name=name,
                type=feed_type,
                url=url,
                query=query,
                tags=tags or [],
            )
            feeds.append(feed)
        else:
            feed = existing.model_copy(
                update={
                    "name": name,
                    "type": feed_type,
                    "url": url or existing.url,
                    "query": query or existing.query,
                    "tags": tags if tags is not None else existing.tags,
                }
            )
            feeds = [feed if item.id == feed_id else item for item in feeds]
        self._write(feeds)
        return feed

    def update(self, feed: Feed) -> Feed:
        feeds = self.list()
        if not any(item.id == feed.id for item in feeds):
            raise FeedNotFoundError(f"Feed not found: {feed.id}")
        self._write([feed if item.id == feed.id else item for item in feeds])
        return feed

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"feeds": []}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise DiscoveryError(f"Invalid feed registry: {self.path}")
        return data

    def _write(self, feeds: list[Feed]) -> None:
        data = {"feeds": [feed.model_dump(mode="json") for feed in feeds]}
        self.path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


class Inbox:
    """Read and write discovered inbox items."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.path = self.workspace / ".researchinfra" / "inbox.yaml"
        self.sources = SourceRegistry(self.workspace)

    def list(self, *, status: InboxStatus | None = None) -> list[InboxItem]:
        data = self._read()
        items = [InboxItem.model_validate(item) for item in data.get("items", [])]
        if status is not None:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda item: item.created_at)

    def get(self, item_id: str) -> InboxItem:
        for item in self.list():
            if item.id == item_id:
                return item
        raise InboxItemNotFoundError(f"Inbox item not found: {item_id}")

    def add_many(self, items: list[InboxItem]) -> list[InboxItem]:
        """Add new inbox items, deduplicating by URL and external id."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.list()
        all_items = list(existing)
        added: list[InboxItem] = []
        for item in items:
            if self._has_duplicate(item, all_items):
                continue
            if self.sources.find_by_url_or_external_id(url=item.url, external_id=item.external_id):
                continue
            all_items.append(item)
            added.append(item)
        self._write(all_items)
        return added

    def promote(self, item_id: str) -> Source:
        item = self.get(item_id)
        existing = self.sources.find_by_url_or_external_id(
            url=item.url, external_id=item.external_id
        )
        if existing is None:
            source = self.sources.add(
                item.url,
                source_type=item.type,
                title=item.title,
                tags=item.tags,
                abstract=item.abstract,
                authors=item.authors,
                published_at=item.published_at,
                external_id=item.external_id,
                pdf_url=item.pdf_url,
                raw_metadata=item.raw_metadata,
            )
        else:
            source = existing
        self._set_status(item_id, "saved")
        return source

    def skip(self, item_id: str) -> InboxItem:
        return self._set_status(item_id, "skipped")

    def _set_status(self, item_id: str, status: InboxStatus) -> InboxItem:
        items = self.list()
        updated: InboxItem | None = None
        for index, item in enumerate(items):
            if item.id == item_id:
                updated = item.model_copy(update={"status": status, "updated_at": utc_now()})
                items[index] = updated
                break
        if updated is None:
            raise InboxItemNotFoundError(f"Inbox item not found: {item_id}")
        self._write(items)
        return updated

    def _has_duplicate(self, item: InboxItem, existing: list[InboxItem]) -> bool:
        normalized = _normalize_url(item.url)
        for other in existing:
            if _normalize_url(other.url) == normalized:
                return True
            if item.external_id and other.external_id == item.external_id:
                return True
        return False

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"items": []}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise DiscoveryError(f"Invalid inbox: {self.path}")
        return data

    def _write(self, items: list[InboxItem]) -> None:
        data = {"items": [item.model_dump(mode="json") for item in items]}
        self.path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


class FeedSyncer:
    """Synchronize configured feeds into the inbox."""

    def __init__(self, workspace: str | Path, *, fetch_text: FetchText | None = None) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.feeds = FeedRegistry(self.workspace)
        self.inbox = Inbox(self.workspace)
        self.fetch_text = fetch_text or _fetch_text

    def sync(self, *, feed_id: str | None = None, limit: int = 20) -> list[InboxItem]:
        feeds = [self.feeds.get(feed_id)] if feed_id else self.feeds.list()
        added: list[InboxItem] = []
        for feed in feeds:
            if not feed.enabled:
                continue
            try:
                discovered = self._discover(feed, limit=limit)
            except ET.ParseError as exc:
                raise DiscoveryError(f"Failed to parse feed {feed.id}: {exc}") from exc
            added.extend(self.inbox.add_many(discovered))
            self.feeds.update(feed.model_copy(update={"last_synced_at": utc_now()}))
        return added

    def _discover(self, feed: Feed, *, limit: int) -> list[InboxItem]:
        if feed.type == "arxiv":
            query_url = _arxiv_query_url(feed.query or "", limit=limit)
            return parse_arxiv_feed(self.fetch_text(query_url), feed=feed, limit=limit)
        if feed.type in {"rss", "atom"}:
            if not feed.url:
                raise DiscoveryError(f"{feed.type} feed has no URL: {feed.id}")
            return parse_rss_or_atom(self.fetch_text(feed.url), feed=feed, limit=limit)
        if feed.type == "web":
            if not feed.url:
                raise DiscoveryError(f"web feed has no URL: {feed.id}")
            return [
                InboxItem(
                    id=_stable_id("inbox", feed.id, feed.url),
                    feed_id=feed.id,
                    type="web",
                    title=feed.name,
                    url=feed.url,
                    tags=feed.tags,
                    raw_metadata={"feed_type": "web"},
                )
            ][:limit]
        raise DiscoveryError(f"Unsupported feed type: {feed.type}")


class SourceEnricher:
    """Enrich existing sources with lightweight metadata."""

    def __init__(self, workspace: str | Path, *, fetch_text: FetchText | None = None) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.sources = SourceRegistry(self.workspace)
        self.fetch_text = fetch_text or _fetch_text

    def enrich(self, source_id: str) -> Source:
        source = self.sources.get(source_id)
        if _is_arxiv_url(source.target):
            enriched = self._enrich_arxiv(source)
            return self.sources.update(enriched)
        return self.sources.update(
            source.model_copy(
                update={
                    "raw_metadata": {
                        **source.raw_metadata,
                        "enrichment_note": "No lightweight enricher available for this source.",
                    }
                }
            )
        )

    def _enrich_arxiv(self, source: Source) -> Source:
        arxiv_id = _extract_arxiv_id(source.target)
        if not arxiv_id:
            return source
        updates: dict[str, object] = {
            "source_type": "paper",
            "external_id": f"arxiv:{arxiv_id}",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            "raw_metadata": {**source.raw_metadata, "arxiv_id": arxiv_id},
        }
        try:
            xml_text = self.fetch_text(_arxiv_query_url(f"id:{arxiv_id}", limit=1))
            feed = Feed(
                id="enrichment",
                name="arXiv enrichment",
                type="arxiv",
                query=f"id:{arxiv_id}",
            )
            parsed = parse_arxiv_feed(xml_text, feed=feed, limit=1)
        except (DiscoveryError, ET.ParseError, URLError, OSError):
            parsed = []
        if parsed:
            item = parsed[0]
            updates.update(
                {
                    "title": item.title or source.title,
                    "abstract": item.abstract or source.abstract,
                    "authors": item.authors or source.authors,
                    "published_at": item.published_at or source.published_at,
                    "external_id": item.external_id or updates["external_id"],
                    "pdf_url": item.pdf_url or updates["pdf_url"],
                    "raw_metadata": {
                        **source.raw_metadata,
                        **item.raw_metadata,
                        "arxiv_id": arxiv_id,
                    },
                }
            )
        return source.model_copy(update=updates)


def parse_arxiv_feed(xml_text: str, *, feed: Feed, limit: int) -> list[InboxItem]:
    """Parse arXiv Atom XML into inbox items."""

    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entries = root.findall("atom:entry", ns)
    items: list[InboxItem] = []
    for entry in entries[:limit]:
        url = _text(entry.find("atom:id", ns)) or ""
        title = _clean_text(_text(entry.find("atom:title", ns)) or "(untitled)")
        abstract = _clean_text(_text(entry.find("atom:summary", ns)) or "")
        authors = [
            _clean_text(_text(author.find("atom:name", ns)) or "")
            for author in entry.findall("atom:author", ns)
        ]
        authors = [author for author in authors if author]
        published_at = _parse_datetime(_text(entry.find("atom:published", ns)))
        arxiv_id = _extract_arxiv_id(url)
        pdf_url = _link_href(entry, ns, title="pdf") or (
            f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None
        )
        external_id = f"arxiv:{arxiv_id}" if arxiv_id else None
        items.append(
            InboxItem(
                id=_stable_id("inbox", external_id or url or title),
                feed_id=feed.id,
                type="paper",
                title=title,
                url=url,
                abstract=abstract or None,
                authors=authors,
                published_at=published_at,
                external_id=external_id,
                pdf_url=pdf_url,
                tags=feed.tags,
                raw_metadata={"source": "arxiv", "query": feed.query},
            )
        )
    return items


def parse_rss_or_atom(xml_text: str, *, feed: Feed, limit: int) -> list[InboxItem]:
    """Parse RSS or Atom XML into inbox items."""

    root = ET.fromstring(xml_text)
    if root.tag.endswith("rss"):
        entries = root.findall("./channel/item")
        return [_rss_item_to_inbox(entry, feed) for entry in entries[:limit]]

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns) or root.findall("entry")
    return [_atom_item_to_inbox(entry, feed, ns) for entry in entries[:limit]]


def _rss_item_to_inbox(entry: ET.Element, feed: Feed) -> InboxItem:
    title = _clean_text(_text(entry.find("title")) or "(untitled)")
    url = _text(entry.find("link")) or feed.url or ""
    abstract = _clean_text(_text(entry.find("description")) or _text(entry.find("summary")) or "")
    published_at = _parse_datetime(_text(entry.find("pubDate")) or _text(entry.find("published")))
    external_id = _text(entry.find("guid"))
    authors = _split_authors(_text(entry.find("author")) or _text(entry.find("creator")))
    return InboxItem(
        id=_stable_id("inbox", external_id or url or title),
        feed_id=feed.id,
        type="web",
        title=title,
        url=url,
        abstract=abstract or None,
        authors=authors,
        published_at=published_at,
        external_id=external_id,
        tags=feed.tags,
        raw_metadata={"source": feed.type},
    )


def _atom_item_to_inbox(entry: ET.Element, feed: Feed, ns: dict[str, str]) -> InboxItem:
    title = _clean_text(
        _text(entry.find("atom:title", ns)) or _text(entry.find("title")) or "(untitled)"
    )
    url = (
        _link_href(entry, ns)
        or _text(entry.find("atom:id", ns))
        or _text(entry.find("id"))
        or feed.url
        or ""
    )
    abstract = _clean_text(
        _text(entry.find("atom:summary", ns))
        or _text(entry.find("summary"))
        or _text(entry.find("atom:content", ns))
        or ""
    )
    authors = [
        _clean_text(_text(author.find("atom:name", ns)) or _text(author.find("name")) or "")
        for author in entry.findall("atom:author", ns) + entry.findall("author")
    ]
    authors = [author for author in authors if author]
    published_at = _parse_datetime(
        _text(entry.find("atom:published", ns))
        or _text(entry.find("published"))
        or _text(entry.find("atom:updated", ns))
        or _text(entry.find("updated"))
    )
    external_id = _text(entry.find("atom:id", ns)) or _text(entry.find("id"))
    return InboxItem(
        id=_stable_id("inbox", external_id or url or title),
        feed_id=feed.id,
        type="web",
        title=title,
        url=url,
        abstract=abstract or None,
        authors=authors,
        published_at=published_at,
        external_id=external_id,
        tags=feed.tags,
        raw_metadata={"source": feed.type},
    )


def _fetch_text(url: str) -> str:
    try:
        with urlopen(url, timeout=30) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except URLError as exc:
        raise DiscoveryError(f"Failed to fetch feed {url}: {exc.reason}") from exc


def _arxiv_query_url(query: str, *, limit: int) -> str:
    return (
        "https://export.arxiv.org/api/query?"
        f"search_query={quote_plus(query)}&start=0&max_results={limit}"
    )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def _normalize_url(value: str) -> str:
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"


def _is_arxiv_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.netloc.lower() == "arxiv.org" and parsed.path.startswith(("/abs/", "/pdf/"))


def _extract_arxiv_id(value: str) -> str | None:
    parsed = urlparse(value)
    path = parsed.path
    if "/abs/" in path:
        return path.split("/abs/", 1)[1].removesuffix(".pdf")
    if "/pdf/" in path:
        return path.split("/pdf/", 1)[1].removesuffix(".pdf")
    if value.startswith("arxiv:"):
        return value.split(":", 1)[1]
    return None


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return element.text.strip()


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _link_href(entry: ET.Element, ns: dict[str, str], *, title: str | None = None) -> str | None:
    links = entry.findall("atom:link", ns) + entry.findall("link")
    for link in links:
        if title is not None and link.attrib.get("title") != title:
            continue
        href = link.attrib.get("href")
        if href:
            return href
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _split_authors(value: str | None) -> list[str]:
    if not value:
        return []
    return [author.strip() for author in value.replace(";", ",").split(",") if author.strip()]
