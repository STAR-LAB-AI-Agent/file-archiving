"""tag 原语单测。"""

from file_organizer.stages.tag import tag_stage


def test_tag_adds_tags(make_record):
    entries = [make_record("a.pdf"), make_record("b.jpg")]
    tag_stage(entries, {"tags": "重要"}, {})
    assert entries[0].tags == ["重要"]
    assert entries[1].tags == ["重要"]


def test_tag_with_where(make_record):
    entries = [make_record("a.pdf", extension="pdf"), make_record("b.jpg", extension="jpg")]
    tag_stage(entries, {"tags": ["扫描"], "where": {"field": "extension", "op": "eq", "value": "jpg"}}, {})
    assert entries[0].tags == []
    assert entries[1].tags == ["扫描"]


def test_tag_no_duplicate(make_record):
    entries = [make_record("a.pdf")]
    tag_stage(entries, {"tags": "x"}, {})
    tag_stage(entries, {"tags": "x"}, {})
    assert entries[0].tags == ["x"]
