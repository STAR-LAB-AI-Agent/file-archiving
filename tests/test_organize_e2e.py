"""端到端集成测试：scan → 默认管道 → plan → apply。"""

from file_organizer.executor import apply_plan
from file_organizer.pipeline import DEFAULT_PIPELINE, run_pipeline
from file_organizer.planner import build_plan
from file_organizer.scanner import scan_directory


def test_organize_end_to_end(tmp_path):
    (tmp_path / "报告.pdf").write_text("pdf")
    (tmp_path / "照片.jpg").write_text("jpg")
    (tmp_path / "数据.xlsx").write_text("xlsx")
    (tmp_path / "未知.xyz").write_text("xyz")

    result = scan_directory(tmp_path)
    entries = run_pipeline(DEFAULT_PIPELINE, result.entries, root=str(tmp_path))
    plan = build_plan(entries, root=str(tmp_path))
    assert plan["summary"]["to_move"] == 4
    assert plan["summary"]["conflicts"] == 0

    out = apply_plan(plan)
    assert out["summary"]["applied"] == 4
    assert (tmp_path / "文档" / "报告.pdf").exists()
    assert (tmp_path / "图片" / "照片.jpg").exists()
    assert (tmp_path / "表格" / "数据.xlsx").exists()
    assert (tmp_path / "其他" / "未知.xyz").exists()
