"""models のテスト"""
from gov_monitor.models import UpdateEvent, MonitorConfig


class TestUpdateEvent:
    def test_create_update_event(self):
        event = UpdateEvent(
            id="abc123",
            url="https://example.com",
            source_url="https://example.com/article",
            title="テスト更新",
            detected_at="2026-04-30T10:00:00+09:00",
            published_at="2026-04-30",
            diff_text="+ 新しい内容",
            summary="テストのサマリー",
            category="新着",
            monitor_id="test_monitor",
        )
        assert event.id == "abc123"
        assert event.category == "新着"


class TestMonitorConfig:
    def test_create_monitor_config_defaults(self):
        config = MonitorConfig(
            id="m1",
            name="テスト",
            url="https://example.com",
            type="rss",
            interval_minutes=15,
        )
        assert config.keywords == []
        assert config.selector == ""
        assert config.notify == []

    def test_create_monitor_config_full(self):
        config = MonitorConfig(
            id="m1",
            name="厚労省",
            url="https://www.mhlw.go.jp/stf/news.rdf",
            type="rss",
            interval_minutes=15,
            keywords=["障害", "補助金"],
            selector="",
            notify=["slack", "sheets"],
        )
        assert "障害" in config.keywords
        assert "slack" in config.notify
