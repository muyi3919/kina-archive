import pytest
from kina_archive.db import ArchiveDB


def test_db_init():
    db = ArchiveDB(":memory:")
    stats = db.get_stats()
    assert stats["total_snapshots"] == 0
    assert stats["unique_urls"] == 0
    db.close()


def test_add_snapshot():
    db = ArchiveDB(":memory:")
    sid = db.add_snapshot("https://example.com", "test.png", "abc123", 1024, 1920, 1080)
    assert sid == 1

    last = db.get_last_snapshot("https://example.com")
    assert last["url"] == "https://example.com"
    assert last["image_hash"] == "abc123"
    db.close()
