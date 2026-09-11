"""filter 原语单测。"""

from file_organizer.stages.filter import filter_stage


def test_filter_eq(make_record):
    entries = [make_record("a.pdf", extension="pdf"), make_record("b.jpg", extension="jpg")]
    out = filter_stage(entries, {"where": {"field": "extension", "op": "eq", "value": "pdf"}}, {})
    assert [e.name for e in out] == ["a.pdf"]


def test_filter_in(make_record):
    entries = [
        make_record("a.pdf", extension="pdf"),
        make_record("b.jpg", extension="jpg"),
        make_record("c.png", extension="png"),
    ]
    out = filter_stage(entries, {"where": {"field": "extension", "op": "in", "value": ["jpg", "png"]}}, {})
    assert [e.name for e in out] == ["b.jpg", "c.png"]


def test_filter_and_gt(make_record):
    entries = [
        make_record("a.pdf", extension="pdf", size=100),
        make_record("b.pdf", extension="pdf", size=200),
        make_record("c.jpg", extension="jpg", size=300),
    ]
    where = {"and": [
        {"field": "extension", "op": "eq", "value": "pdf"},
        {"field": "size", "op": "gt", "value": 150},
    ]}
    out = filter_stage(entries, {"where": where}, {})
    assert [e.name for e in out] == ["b.pdf"]


def test_filter_or(make_record):
    entries = [
        make_record("a.pdf", extension="pdf"),
        make_record("b.jpg", extension="jpg"),
        make_record("c.png", extension="png"),
    ]
    where = {"or": [
        {"field": "extension", "op": "eq", "value": "jpg"},
        {"field": "extension", "op": "eq", "value": "png"},
    ]}
    out = filter_stage(entries, {"where": where}, {})
    assert [e.name for e in out] == ["b.jpg", "c.png"]


def test_filter_regex(make_record):
    entries = [
        make_record("IMG_0001.jpg", extension="jpg"),
        make_record("notes.txt", extension="txt"),
    ]
    where = {"field": "name", "op": "regex", "value": r"^IMG_\d+\.jpg$"}
    out = filter_stage(entries, {"where": where}, {})
    assert [e.name for e in out] == ["IMG_0001.jpg"]


def test_filter_none_keeps_all(make_record):
    entries = [make_record("a.pdf"), make_record("b.jpg")]
    assert len(filter_stage(entries, {}, {})) == 2
