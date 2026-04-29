"""M3: 状態管理のテスト"""
import pytest
import tempfile
from pathlib import Path
from gov_monitor.state_store import StateStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_state.db"
    store = StateStore(db_path=str(db_path))
    store.initialize()
    return store


class TestStateStore:
    def test_save_and_load_seen_ids(self, store):
        store.mark_seen(monitor_id="m1", entry_id="https://example.com/1")
        assert store.is_seen(monitor_id="m1", entry_id="https://example.com/1")

    def test_unseen_entry_returns_false(self, store):
        assert not store.is_seen(monitor_id="m1", entry_id="https://example.com/unknown")

    def test_get_seen_ids_for_monitor(self, store):
        store.mark_seen("m1", "https://example.com/1")
        store.mark_seen("m1", "https://example.com/2")
        store.mark_seen("m2", "https://example.com/3")
        ids = store.get_seen_ids(monitor_id="m1")
        assert ids == {"https://example.com/1", "https://example.com/2"}

    def test_save_content_hash(self, store):
        store.save_content_hash(monitor_id="m1", hash_value="abc123")
        assert store.get_content_hash(monitor_id="m1") == "abc123"

    def test_get_content_hash_returns_none_if_not_set(self, store):
        assert store.get_content_hash(monitor_id="new_monitor") is None

    def test_mark_seen_is_idempotent(self, store):
        store.mark_seen("m1", "https://example.com/1")
        store.mark_seen("m1", "https://example.com/1")
        ids = store.get_seen_ids("m1")
        assert len(ids) == 1
