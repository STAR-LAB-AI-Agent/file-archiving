"""classify 原语单测。"""

import pytest

from file_organizer.stages.classify import classify_stage
from file_organizer.stages.where import StageError

RULES = {"type_rules": {"文档": ["pdf"], "图片": ["jpg"]}, "default_folder": "其他"}


def test_classify_by_type(make_record):
    entries = [
        make_record("a.pdf", extension="pdf"),
        make_record("b.jpg", extension="jpg"),
        make_record("c.xyz", extension="xyz"),
    ]
    classify_stage(entries, {"by": "type"}, {"rules": RULES})
    assert [e.category for e in entries] == ["文档", "图片", "其他"]


def test_classify_by_name(make_record):
    entries = [make_record("劳动合同.pdf"), make_record("发票扫描.png")]
    ctx = {"rules": {"name_rules": {"合同": ["合同"], "发票": ["发票"]}, "default_folder": "其他"}}
    classify_stage(entries, {"by": "name"}, ctx)
    assert [e.category for e in entries] == ["合同", "发票"]


def test_classify_by_content(tmp_path, make_record):
    f1 = tmp_path / "a.txt"
    f1.write_text("本合同 甲方 乙方", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("发票 报销 金额", encoding="utf-8")
    entries = [make_record("a.txt", path=str(f1)), make_record("b.txt", path=str(f2))]
    ctx = {"rules": {"content_rules": {"合同": ["合同", "甲方"], "发票": ["发票", "报销"]}, "default_folder": "其他"}}
    classify_stage(entries, {"by": "content"}, ctx)
    assert [e.category for e in entries] == ["合同", "发票"]
