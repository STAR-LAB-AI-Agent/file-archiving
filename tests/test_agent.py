"""agent（智能体入口）单测：意图解析、管道构建、端到端执行。"""

import pytest

from file_organizer.agent import AgentError, build_pipeline, parse_intent, run_instruction


# ---------- parse_intent ----------

def test_parse_intent_organize():
    assert parse_intent("把下载文件夹整理一下")["name"] == "organize"
    assert parse_intent("按类型整理")["name"] == "organize"


def test_parse_intent_classify():
    intent = parse_intent("按文件名分类")
    assert intent["name"] == "classify"
    assert intent["params"]["by"] == "name"


def test_parse_intent_rename():
    intent = parse_intent("重命名为 {date}_{index:03d}{suffix}")
    assert intent["name"] == "rename"
    assert intent["params"]["template"] == "{date}_{index:03d}{suffix}"


def test_parse_intent_move():
    intent = parse_intent("移到 归档")
    assert intent["name"] == "move"
    assert intent["params"]["target"] == "归档"


def test_parse_intent_unknown():
    with pytest.raises(AgentError):
        parse_intent("随便看看")


def test_parse_intent_empty():
    with pytest.raises(AgentError):
        parse_intent("")


# ---------- build_pipeline ----------

def test_build_pipeline_organize():
    p = build_pipeline({"name": "organize", "params": {}})
    assert [s["op"] for s in p["stages"]] == ["classify", "move"]


def test_build_pipeline_rename_requires_template():
    with pytest.raises(AgentError):
        build_pipeline({"name": "rename", "params": {"template": None}})


# ---------- run_instruction ----------

def test_run_instruction_organize_execute(tmp_path):
    (tmp_path / "a.pdf").write_text("pdf")
    (tmp_path / "b.jpg").write_text("jpg")
    out = run_instruction("按类型整理", str(tmp_path), execute=True)
    assert out["intent"]["name"] == "organize"
    assert out["result"]["summary"]["applied"] == 2
    assert (tmp_path / "文档" / "a.pdf").exists()
    assert (tmp_path / "图片" / "b.jpg").exists()


def test_run_instruction_dry_no_side_effect(tmp_path):
    (tmp_path / "a.pdf").write_text("pdf")
    out = run_instruction("按类型整理", str(tmp_path), execute=False)
    assert out["result"] is None
    assert (tmp_path / "a.pdf").exists()  # 未移动


def test_run_instruction_rename(tmp_path):
    (tmp_path / "IMG_0001.jpg").write_text("1")
    (tmp_path / "IMG_0002.jpg").write_text("2")
    out = run_instruction("重命名为 {date}_{index:03d}{suffix}", str(tmp_path), execute=True)
    assert out["result"]["summary"]["applied"] == 2
    names = sorted(p.name for p in tmp_path.iterdir() if p.name != ".file_organizer")
    assert len(names) == 2
    assert all(n.endswith(".jpg") for n in names)


def test_run_instruction_move_to_target(tmp_path):
    (tmp_path / "a.pdf").write_text("pdf")
    out = run_instruction("移到 归档", str(tmp_path), execute=True)
    assert out["result"]["summary"]["applied"] == 1
    assert (tmp_path / "归档" / "a.pdf").exists()
