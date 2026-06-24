import pytest
import os
import tempfile
from kina_archive.db import ArchiveDB
from kina_archive.compare import ImageComparator, _parse_regions
from PIL import Image


def test_db_init():
    db = ArchiveDB(":memory:")
    stats = db.get_stats()
    assert stats["total_snapshots"] == 0
    assert stats["unique_urls"] == 0
    db.close()


def test_db_context_manager():
    with ArchiveDB(":memory:") as db:
        stats = db.get_stats()
        assert stats["total_snapshots"] == 0


def test_add_snapshot():
    db = ArchiveDB(":memory:")
    sid = db.add_snapshot("https://example.com", "test.png", "abc123", 1024, 1920, 1080)
    assert sid == 1

    last = db.get_last_snapshot("https://example.com")
    assert last["url"] == "https://example.com"
    assert last["image_hash"] == "abc123"
    db.close()


def test_parse_regions_absolute():
    regions = _parse_regions("0,0,1920,300", 1920, 1080)
    assert regions == [(0, 0, 1920, 300)]


def test_parse_regions_percentage():
    regions = _parse_regions("0,0,100%,20%", 1920, 1080)
    assert regions == [(0, 0, 1920, 216)]


def test_parse_regions_multiple():
    regions = _parse_regions("0,0,100%,10%;0,800,1920,280", 1920, 1080)
    assert len(regions) == 2
    assert regions[0] == (0, 0, 1920, 108)
    assert regions[1] == (0, 800, 1920, 280)


def test_image_comparator_phash():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建两张相同的测试图片
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        p1 = os.path.join(tmpdir, "test1.png")
        p2 = os.path.join(tmpdir, "test2.png")
        img1.save(p1)
        img2.save(p2)

        comp = ImageComparator(tmpdir)
        sim, diff_path, count = comp.compare(p1, p2, mode="phash")
        assert sim == 1.0
        assert count == 0


def test_image_comparator_pixel_same():
    with tempfile.TemporaryDirectory() as tmpdir:
        img1 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img2 = Image.new("RGB", (100, 100), color=(128, 128, 128))
        p1 = os.path.join(tmpdir, "test1.png")
        p2 = os.path.join(tmpdir, "test2.png")
        img1.save(p1)
        img2.save(p2)

        comp = ImageComparator(tmpdir)
        sim, diff_path, count = comp.compare(p1, p2, mode="pixel")
        assert sim == 1.0
        assert count == 0
