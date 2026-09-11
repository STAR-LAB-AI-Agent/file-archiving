"""rename 原语单测。"""

import re

from file_organizer.stages.rename import rename_stage


def test_rename_template_index(make_record):
    entries = [make_record("a.jpg", extension="jpg"), make_record("b.jpg", extension="jpg")]
    rename_stage(entries, {"template": "{date}_{index:03d}{suffix}"}, {})
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_001\.jpg", entries[0].new_name)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_002\.jpg", entries[1].new_name)


def test_rename_with_where(make_record):
    entries = [
        make_record("a.jpg", extension="jpg", category="图片"),
        make_record("b.pdf", extension="pdf", category="文档"),
    ]
    rename_stage(
        entries,
        {"template": "{category}_{index}{suffix}", "where": {"field": "category", "op": "eq", "value": "图片"}},
        {},
    )
    assert entries[0].new_name == "图片_1.jpg"
    assert entries[1].new_name is None
