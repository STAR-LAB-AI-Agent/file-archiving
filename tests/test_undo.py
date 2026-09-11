"""undo 一键撤销单测。"""

from file_organizer.executor import apply_plan
from file_organizer.planner import build_plan
from file_organizer.undo import undo_last


def _organize_once(make_record, tmp_path):
    (tmp_path / "a.pdf").write_text("a")
    entries = [
        make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档"))
    ]
    plan = build_plan(entries, root=str(tmp_path))
    apply_plan(plan)


def test_undo_last_restores(make_record, tmp_path):
    _organize_once(make_record, tmp_path)
    assert (tmp_path / "文档" / "a.pdf").exists()
    result = undo_last(str(tmp_path))
    assert result["undone"] == 1
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "文档" / "a.pdf").exists()


def test_undo_no_history(tmp_path):
    result = undo_last(str(tmp_path))
    assert result["undone"] == 0


def test_undo_cleans_empty_dirs(make_record, tmp_path):
    (tmp_path / "a.pdf").write_text("a")
    entries = [make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档"))]
    plan = build_plan(entries, root=str(tmp_path))
    apply_plan(plan)
    assert (tmp_path / "文档" / "a.pdf").exists()

    result = undo_last(str(tmp_path))
    assert result["undone"] == 1
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "文档").exists()  # 空分类目录被清理


def test_undo_cleans_nested_empty_dirs(make_record, tmp_path):
    (tmp_path / "a.pdf").write_text("a")
    target = str(tmp_path / "马克思主义" / "文档")
    entries = [make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="马克思主义/文档", target=target)]
    plan = build_plan(entries, root=str(tmp_path))
    apply_plan(plan)
    assert (tmp_path / "马克思主义" / "文档" / "a.pdf").exists()

    result = undo_last(str(tmp_path))
    assert result["undone"] == 1
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "马克思主义").exists()  # 两级空目录都被清理
