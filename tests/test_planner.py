"""planner 单测：计划生成与冲突检测。"""

from file_organizer.planner import build_plan


def test_build_plan_move_and_rename(make_record, tmp_path):
    root = str(tmp_path)
    entries = [
        make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档")),
        make_record(
            "b.jpg",
            path=str(tmp_path / "b.jpg"),
            category="图片",
            target=str(tmp_path / "图片"),
            new_name="2026-01-01_001.jpg",
        ),
    ]
    plan = build_plan(entries, root=root)
    assert plan["summary"]["to_move"] == 1
    assert plan["summary"]["to_move_and_rename"] == 1
    assert len(plan["actions"]) == 2


def test_build_plan_skips_noop(make_record, tmp_path):
    e = make_record("a.pdf", path=str(tmp_path / "a.pdf"), target=str(tmp_path))
    plan = build_plan([e], root=str(tmp_path))
    assert plan["summary"]["skip"] == 1
    assert plan["actions"] == []


def test_build_plan_conflict_target_exists(make_record, tmp_path):
    (tmp_path / "文档").mkdir()
    (tmp_path / "文档" / "a.pdf").write_text("x")
    entries = [
        make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档"))
    ]
    plan = build_plan(entries, root=str(tmp_path))
    assert plan["summary"]["conflicts"] == 1
    assert plan["actions"][0]["conflict"] == "目标已存在"


def test_build_plan_conflict_duplicate_target(make_record, tmp_path):
    # 两个不同来源的同名文件，均要移动到同一目录 → 最终目标路径相同 → 冲突
    entries = [
        make_record("a.pdf", path=str(tmp_path / "x" / "a.pdf"), category="文档", target=str(tmp_path / "文档")),
        make_record("a.pdf", path=str(tmp_path / "y" / "a.pdf"), category="文档", target=str(tmp_path / "文档")),
    ]
    plan = build_plan(entries, root=str(tmp_path))
    assert plan["summary"]["conflicts"] == 1
