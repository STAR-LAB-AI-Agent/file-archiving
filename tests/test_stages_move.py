"""move 原语单测。"""

from pathlib import Path

from file_organizer.stages.move import move_stage


def test_move_by_category(make_record):
    entries = [make_record("a.pdf", category="文档"), make_record("b.jpg", category="图片")]
    move_stage(entries, {"rule": "by_category"}, {"root": "/root"})
    assert Path(entries[0].target) == Path("/root") / "文档"
    assert Path(entries[1].target) == Path("/root") / "图片"


def test_move_by_category_default_folder(make_record):
    entries = [make_record("c.xyz", category=None)]
    move_stage(entries, {"rule": "by_category"}, {"root": "/root", "rules": {"default_folder": "其他"}})
    assert Path(entries[0].target) == Path("/root") / "其他"


def test_move_to_path_absolute(make_record):
    entries = [make_record("a.pdf")]
    move_stage(entries, {"rule": "to_path", "target": "/archive"}, {"root": "/root"})
    assert Path(entries[0].target) == Path("/archive")


def test_move_by_category_preserve(make_record):
    # 嵌套文件就地分类：目标 = 文件所在目录 / 分类，而非 root / 分类（不扁平化）
    entries = [make_record("a.pdf", path="/root/项目/a.pdf", category="文档")]
    move_stage(entries, {"rule": "by_category", "preserve": True}, {"root": "/root"})
    assert Path(entries[0].target) == Path("/root") / "项目" / "文档"


def test_move_by_category_preserve_idempotent(make_record):
    # 已在该分类目录下：原地不动，避免 文档/文档 二次嵌套
    entries = [make_record("a.pdf", path="/root/文档/a.pdf", category="文档")]
    move_stage(entries, {"rule": "by_category", "preserve": True}, {"root": "/root"})
    assert Path(entries[0].target) == Path("/root") / "文档"


def test_move_by_category_preserve_hierarchical(make_record):
    entries = [make_record("a.pdf", path="/root/a.pdf", category="马克思主义/文档")]
    move_stage(entries, {"rule": "by_category", "preserve": True}, {"root": "/root"})
    assert Path(entries[0].target) == Path("/root") / "马克思主义" / "文档"


def test_move_to_path_absolute_sets_external_target(make_record, tmp_path):
    outside = tmp_path / "elsewhere"  # tmp_path 为绝对路径，跨平台有效
    entries = [make_record("a.docx", path=str(tmp_path / "a.docx"))]
    move_stage(entries, {"rule": "to_path", "target": str(outside)}, {"root": str(tmp_path)})
    assert entries[0].external_target is True


def test_move_to_path_relative_not_external(make_record):
    entries = [make_record("a.docx", path="/root/a.docx")]
    move_stage(entries, {"rule": "to_path", "target": "归档"}, {"root": "/root"})
    assert entries[0].external_target is False
