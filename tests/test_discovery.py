import yaml

from researchinfra.discovery import (
    FeedRegistry,
    FeedSyncer,
    Inbox,
    SourceEnricher,
    parse_arxiv_feed,
    parse_rss_or_atom,
)
from researchinfra.schemas import Feed
from researchinfra.sources import SourceRegistry

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/1234.5678v1</id>
    <updated>2024-01-02T00:00:00Z</updated>
    <published>2024-01-01T00:00:00Z</published>
    <title> Demo Arxiv Paper </title>
    <summary> A short abstract. </summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <link title="pdf" href="https://arxiv.org/pdf/1234.5678v1"/>
  </entry>
</feed>
"""


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>RSS Research Note</title>
      <link>https://example.com/research-note</link>
      <description>Short summary.</description>
      <guid>rss-note-1</guid>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <author>Ada Lovelace</author>
    </item>
  </channel>
</rss>
"""


def test_feed_registry_adds_arxiv_feed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registry = FeedRegistry(tmp_path)

    feed = registry.add(
        name="MLLM",
        feed_type="arxiv",
        query='cat:cs.CV AND "multimodal"',
        tags=["mllm"],
    )

    assert feed.id.startswith("feed-")
    assert feed.type == "arxiv"
    assert (tmp_path / ".researchinfra" / "feeds.yaml").exists()
    data = yaml.safe_load((tmp_path / ".researchinfra" / "feeds.yaml").read_text())
    assert data["feeds"][0]["type"] == "arxiv"


def test_parse_arxiv_feed_extracts_metadata() -> None:
    feed = Feed(id="feed-arxiv", name="arXiv", type="arxiv", query="demo", tags=["demo"])

    items = parse_arxiv_feed(ARXIV_XML, feed=feed, limit=5)

    assert len(items) == 1
    item = items[0]
    assert item.type == "paper"
    assert item.title == "Demo Arxiv Paper"
    assert item.authors == ["Ada Lovelace", "Grace Hopper"]
    assert item.external_id == "arxiv:1234.5678v1"
    assert item.pdf_url == "https://arxiv.org/pdf/1234.5678v1"
    assert item.tags == ["demo"]


def test_parse_rss_feed_extracts_metadata() -> None:
    feed = Feed(id="feed-rss", name="RSS", type="rss", url="https://example.com/feed.xml")

    items = parse_rss_or_atom(RSS_XML, feed=feed, limit=5)

    assert len(items) == 1
    item = items[0]
    assert item.title == "RSS Research Note"
    assert item.url == "https://example.com/research-note"
    assert item.abstract == "Short summary."
    assert item.external_id == "rss-note-1"


def test_feed_sync_deduplicates_existing_inbox_items(tmp_path) -> None:  # type: ignore[no-untyped-def]
    registry = FeedRegistry(tmp_path)
    feed = registry.add(name="MLLM", feed_type="arxiv", query="demo")
    syncer = FeedSyncer(tmp_path, fetch_text=lambda _url: ARXIV_XML)

    first = syncer.sync(feed_id=feed.id, limit=5)
    second = syncer.sync(feed_id=feed.id, limit=5)

    assert len(first) == 1
    assert second == []
    assert len(Inbox(tmp_path).list()) == 1


def test_inbox_promote_and_skip_workflow(tmp_path) -> None:  # type: ignore[no-untyped-def]
    feed = FeedRegistry(tmp_path).add(name="MLLM", feed_type="arxiv", query="demo")
    [item] = FeedSyncer(tmp_path, fetch_text=lambda _url: ARXIV_XML).sync(feed_id=feed.id, limit=5)
    inbox = Inbox(tmp_path)

    source = inbox.promote(item.id)

    assert source.title == "Demo Arxiv Paper"
    assert source.external_id == "arxiv:1234.5678v1"
    assert inbox.get(item.id).status == "saved"

    skipped = inbox.skip(item.id)
    assert skipped.status == "skipped"


def test_inbox_deduplicates_against_existing_sources(tmp_path) -> None:  # type: ignore[no-untyped-def]
    SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678v1",
        source_type="paper",
        external_id="arxiv:1234.5678v1",
    )
    feed = FeedRegistry(tmp_path).add(name="MLLM", feed_type="arxiv", query="demo")

    added = FeedSyncer(tmp_path, fetch_text=lambda _url: ARXIV_XML).sync(feed_id=feed.id, limit=5)

    assert added == []
    assert Inbox(tmp_path).list() == []


def test_source_enricher_updates_arxiv_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = SourceRegistry(tmp_path).add(
        "https://arxiv.org/abs/1234.5678v1",
        source_type="paper",
        title="Old Title",
    )

    enriched = SourceEnricher(tmp_path, fetch_text=lambda _url: ARXIV_XML).enrich(source.id)

    assert enriched.title == "Demo Arxiv Paper"
    assert enriched.abstract == "A short abstract."
    assert enriched.authors == ["Ada Lovelace", "Grace Hopper"]
    assert enriched.external_id == "arxiv:1234.5678v1"
    assert enriched.pdf_url == "https://arxiv.org/pdf/1234.5678v1"
