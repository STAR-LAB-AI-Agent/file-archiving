"""dedup 原语单测。"""

from file_organizer.stages.dedup import dedup_stage


def test_dedup_by_name(make_record):
    entries = [
        make_record("a.pdf", path="/r/1/a.pdf"),
        make_record("a.pdf", path="/r/2/a.pdf"),
        make_record("b.pdf", path="/r/3/b.pdf"),
    ]
    dedup_stage(entries, {"by": "name", "keep": "first"}, {})
    assert entries[0].is_kept is True
    assert entries[1].is_kept is False
    assert entries[0].dup_group == entries[1].dup_group
    assert entries[2].is_kept is True
    assert entries[2].dup_group is None


def test_dedup_by_content_hash(tmp_path, make_record):
    (tmp_path / "a.txt").write_text("same content")
    (tmp_path / "b.txt").write_text("same content")
    (tmp_path / "c.txt").write_text("different")
    entries = [
        make_record("a.txt", path=str(tmp_path / "a.txt")),
        make_record("b.txt", path=str(tmp_path / "b.txt")),
        make_record("c.txt", path=str(tmp_path / "c.txt")),
    ]
    dedup_stage(entries, {"by": "content_hash", "keep": "first"}, {})
    assert entries[0].is_kept is True
    assert entries[1].is_kept is False
    assert entries[0].dup_group == entries[1].dup_group
    assert entries[2].is_kept is True
    assert entries[2].dup_group is None
