from kbflow.sync.sync_kb import detect_orphans, sync_directory


def test_sync_directory_hash_incremental(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "a.txt").write_text("hello", encoding="utf-8")
    stats = sync_directory(src, dst)
    assert "a.txt" in stats["copied"]

    stats2 = sync_directory(src, dst)
    assert "a.txt" in stats2["skipped"]

    (src / "a.txt").write_text("changed", encoding="utf-8")
    stats3 = sync_directory(src, dst)
    assert "a.txt" in stats3["updated"]


def test_detect_orphans(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("x", encoding="utf-8")
    (dst / "a.txt").write_text("x", encoding="utf-8")
    (dst / "b.txt").write_text("orphan", encoding="utf-8")
    orphans = detect_orphans(src, dst)
    assert "b.txt" in orphans
    assert "a.txt" not in orphans
