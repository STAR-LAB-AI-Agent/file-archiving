"""sort 原语单测。"""

from file_organizer.stages.sort import sort_stage


def test_sort_by_size_desc(make_record):
    entries = [make_record("a", size=10), make_record("b", size=30), make_record("c", size=20)]
    out = sort_stage(entries, {"by": "size", "order": "desc"}, {})
    assert [e.size for e in out] == [30, 20, 10]


def test_sort_by_name_asc(make_record):
    entries = [make_record("b.txt"), make_record("a.txt"), make_record("c.txt")]
    out = sort_stage(entries, {"by": "name"}, {})
    assert [e.name for e in out] == ["a.txt", "b.txt", "c.txt"]


def test_sort_by_mtime(make_record):
    entries = [make_record("a", mtime=3), make_record("b", mtime=1), make_record("c", mtime=2)]
    out = sort_stage(entries, {"by": "mtime"}, {})
    assert [e.mtime for e in out] == [1, 2, 3]
