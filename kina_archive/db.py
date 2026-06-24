import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class ArchiveDB:
    def __init__(self, db_path: str = "archive.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                image_path TEXT NOT NULL,
                image_hash TEXT,
                file_size INTEGER,
                width INTEGER,
                height INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                old_snapshot_id INTEGER,
                new_snapshot_id INTEGER,
                diff_path TEXT,
                similarity REAL,
                pixel_diff_count INTEGER,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (old_snapshot_id) REFERENCES snapshots(id),
                FOREIGN KEY (new_snapshot_id) REFERENCES snapshots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_url ON snapshots(url);
            CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_changes_url ON changes(url);
        """)
        self.conn.commit()

    def add_snapshot(self, url: str, image_path: str, img_hash: str,
                     size: int, width: int, height: int) -> int:
        cursor = self.conn.execute(
            """INSERT INTO snapshots
               (url, timestamp, image_path, image_hash, file_size, width, height)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, datetime.now().isoformat(), image_path, img_hash, size, width, height)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_last_snapshot(self, url: str) -> Optional[sqlite3.Row]:
        cursor = self.conn.execute(
            "SELECT * FROM snapshots WHERE url = ? ORDER BY timestamp DESC LIMIT 1",
            (url,)
        )
        return cursor.fetchone()

    def get_snapshots(self, url: str, limit: int = 50) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            "SELECT * FROM snapshots WHERE url = ? ORDER BY timestamp DESC LIMIT ?",
            (url, limit)
        )
        return cursor.fetchall()

    def add_change(self, url: str, old_id: int, new_id: int,
                   diff_path: str, similarity: float, pixel_diff: int):
        self.conn.execute(
            """INSERT INTO changes
               (url, old_snapshot_id, new_snapshot_id, diff_path, similarity, pixel_diff_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (url, old_id, new_id, diff_path, similarity, pixel_diff)
        )
        self.conn.commit()

    def get_changes(self, url: str, limit: int = 20) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """SELECT c.*, s1.image_path as old_path, s2.image_path as new_path
               FROM changes c
               LEFT JOIN snapshots s1 ON c.old_snapshot_id = s1.id
               LEFT JOIN snapshots s2 ON c.new_snapshot_id = s2.id
               WHERE c.url = ? ORDER BY c.detected_at DESC LIMIT ?""",
            (url, limit)
        )
        return cursor.fetchall()

    def get_all_urls(self) -> List[str]:
        cursor = self.conn.execute(
            "SELECT DISTINCT url FROM snapshots ORDER BY url"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        cursor = self.conn.execute(
            "SELECT COUNT(*) as total, COUNT(DISTINCT url) as urls FROM snapshots"
        )
        snap = cursor.fetchone()
        cursor = self.conn.execute("SELECT COUNT(*) as total FROM changes")
        ch = cursor.fetchone()
        return {"total_snapshots": snap["total"], "unique_urls": snap["urls"], "total_changes": ch["total"]}

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
