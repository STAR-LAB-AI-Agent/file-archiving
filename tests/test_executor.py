"""executor 单测：落盘执行、冲突策略、dry-run。"""

from file_organizer.executor import apply_plan
from file_organizer.planner import build_plan


def _plan_two_files(make_record, tmp_path):
    (tmp_path / "a.pdf").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    entries = [
        make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档")),
        make_record("b.txt", path=str(tmp_path / "b.txt"), category="文本", target=str(tmp_path / "文本")),
    ]
    return build_plan(entries, root=str(tmp_path))


def test_apply_plan_moves_files(make_record, tmp_path):
    plan = _plan_two_files(make_record, tmp_path)
    result = apply_plan(plan)
    assert result["summary"]["applied"] == 2
    assert (tmp_path / "文档" / "a.pdf").exists()
    assert (tmp_path / "文本" / "b.txt").exists()
    assert not (tmp_path / "a.pdf").exists()


def test_apply_plan_conflict_skip(make_record, tmp_path):
    (tmp_path / "a.pdf").write_text("src")
    (tmp_path / "文档").mkdir()
    (tmp_path / "文档" / "a.pdf").write_text("dst")
    entries = [
        make_record("a.pdf", path=str(tmp_path / "a.pdf"), category="文档", target=str(tmp_path / "文档"))
    ]
    plan = build_plan(entries, root=str(tmp_path))
    assert plan["summary"]["conflicts"] == 1
    result = apply_plan(plan, conflict_policy="skip")
    assert result["summary"]["applied"] == 0
    assert result["summary"]["skipped"] == 1
    assert (tmp_path / "a.pdf").exists()  # 未移动


def test_apply_plan_dry_run(make_record, tmp_path):
    plan = _plan_two_files(make_record, tmp_path)
    result = apply_plan(plan, dry_run=True)
    assert result["summary"]["applied"] == 0
    assert (tmp_path / "a.pdf").exists()


def test_apply_plan_only(make_record, tmp_path):
    plan = _plan_two_files(make_record, tmp_path)
    ids = [a["id"] for a in plan["actions"]]
    result = apply_plan(plan, only={ids[0]})
    assert result["summary"]["applied"] == 1
    assert result["summary"]["skipped"] == 1


def test_apply_plan_exclude(make_record, tmp_path):
    plan = _plan_two_files(make_record, tmp_path)
    ids = [a["id"] for a in plan["actions"]]
    result = apply_plan(plan, exclude={ids[0]})
    assert result["summary"]["applied"] == 1
    assert result["summary"]["skipped"] == 1


def test_apply_plan_external_target_cross_root(make_record, tmp_path):
    # 显式绝对路径目标（external_target=True）允许跨根目录移动
    (tmp_path / "a.docx").write_text("doc")
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    entries = [make_record("a.docx", path=str(tmp_path / "a.docx"), target=str(outside), external_target=True)]
    plan = build_plan(entries, root=str(tmp_path))
    result = apply_plan(plan)
    assert result["summary"]["applied"] == 1
    assert (outside / "a.docx").exists()
    assert not (tmp_path / "a.docx").exists()


def test_apply_plan_rejects_cross_root_by_default(make_record, tmp_path):
    # 默认（external_target=False）越界被拒
    (tmp_path / "a.docx").write_text("doc")
    outside = tmp_path.parent / "outside2"
    outside.mkdir(exist_ok=True)
    entries = [make_record("a.docx", path=str(tmp_path / "a.docx"), target=str(outside))]
    plan = build_plan(entries, root=str(tmp_path))
    result = apply_plan(plan)
    assert result["summary"]["failed"] == 1
    assert (tmp_path / "a.docx").exists()  # 未移动
