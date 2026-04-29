import sqlite3


class StateStore:
    def __init__(self, db_path: str = "gov_monitor_state.db"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_entries (
                monitor_id TEXT NOT NULL,
                entry_id TEXT NOT NULL,
                PRIMARY KEY (monitor_id, entry_id)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS content_hashes (
                monitor_id TEXT PRIMARY KEY,
                hash_value TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn

    def mark_seen(self, monitor_id: str, entry_id: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO seen_entries (monitor_id, entry_id) VALUES (?, ?)",
            (monitor_id, entry_id),
        )
        conn.commit()

    def is_seen(self, monitor_id: str, entry_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT 1 FROM seen_entries WHERE monitor_id = ? AND entry_id = ?",
            (monitor_id, entry_id),
        ).fetchone()
        return row is not None

    def get_seen_ids(self, monitor_id: str) -> set[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT entry_id FROM seen_entries WHERE monitor_id = ?",
            (monitor_id,),
        ).fetchall()
        return {row[0] for row in rows}

    def save_content_hash(self, monitor_id: str, hash_value: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO content_hashes (monitor_id, hash_value) VALUES (?, ?)",
            (monitor_id, hash_value),
        )
        conn.commit()

    def get_content_hash(self, monitor_id: str) -> str | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT hash_value FROM content_hashes WHERE monitor_id = ?",
            (monitor_id,),
        ).fetchone()
        return row[0] if row else None
