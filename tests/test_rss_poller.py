"""M1: RSSポーラーのテスト"""
from pathlib import Path
import pytest
from gov_monitor.pollers.rss_poller import RSSPoller, RSSEntry


FIXTURES = Path(__file__).parent / "fixtures"


class TestRSSPoller:
    def test_parse_feed_returns_entries(self):
        feed_content = (FIXTURES / "mhlw_feed.xml").read_text()
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(feed_content)
        assert len(entries) == 2

    def test_entry_has_required_fields(self):
        feed_content = (FIXTURES / "mhlw_feed.xml").read_text()
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(feed_content)
        entry = entries[0]
        assert entry.id == "https://www.mhlw.go.jp/stf/newpage_72919.html"
        assert entry.title == "第55回社会保障審議会障害者部会 資料"
        assert entry.url == "https://www.mhlw.go.jp/stf/newpage_72919.html"
        assert entry.published_at == "2026-04-28T14:00:00+09:00"

    def test_deduplicate_returns_only_new_entries(self):
        feed_content = (FIXTURES / "mhlw_feed.xml").read_text()
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(feed_content)
        seen_ids = {"https://www.mhlw.go.jp/stf/newpage_72919.html"}
        new_entries = poller.filter_new(entries, seen_ids)
        assert len(new_entries) == 1
        assert new_entries[0].url == "https://www.mhlw.go.jp/stf/newpage_72800.html"

    def test_deduplicate_with_empty_seen_returns_all(self):
        feed_content = (FIXTURES / "mhlw_feed.xml").read_text()
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(feed_content)
        new_entries = poller.filter_new(entries, seen_ids=set())
        assert len(new_entries) == 2

    def test_deduplicate_with_all_seen_returns_empty(self):
        feed_content = (FIXTURES / "mhlw_feed.xml").read_text()
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(feed_content)
        all_ids = {e.id for e in entries}
        new_entries = poller.filter_new(entries, seen_ids=all_ids)
        assert new_entries == []

    def test_parse_empty_feed_returns_empty_list(self):
        empty_feed = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/">
  <channel><title>Empty</title><link>https://example.com</link></channel>
</rdf:RDF>"""
        poller = RSSPoller(url="https://example.com/feed.rdf")
        entries = poller.parse(empty_feed)
        assert entries == []
