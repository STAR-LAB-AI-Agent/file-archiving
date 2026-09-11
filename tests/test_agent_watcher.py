"""监听触发式智能体整理单测（不真正调用大模型、不启动 watchdog）。"""

import pytest

from file_organizer.agent_watcher import (
    ChangeCollector,
    ask_pipeline,
    build_change_prompt,
    organize_once,
    parse_pipeline_json,
)


def test_parse_pipeline_json_plain():
    assert parse_pipeline_json('{"stages":[{"op":"move"}]}') == {"stages": [{"op": "move"}]}


def test_parse_pipeline_json_code_fence():
    raw = '```json\n{"stages":[{"op":"move"}]}\n```'
    assert parse_pipeline_json(raw) == {"stages": [{"op": "move"}]}


def test_build_change_prompt_lists_changed(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    prompt = build_change_prompt(str(tmp_path), [str(tmp_path / "a.pdf")])
    assert str(tmp_path) in prompt
    assert "a.pdf" in prompt


def test_ask_pipeline_with_fake_llm(tmp_path):
    def fake_llm(system, user):
        return '{"stages":[{"op":"classify","by":"type"},{"op":"move","rule":"by_category"}]}'

    desc = ask_pipeline(str(tmp_path), [str(tmp_path / "a.pdf")], llm=fake_llm)
    assert desc["stages"][0]["op"] == "classify"


def test_ask_pipeline_rejects_empty_stages(tmp_path):
    def fake_llm(system, user):
        return '{"stages":[]}'

    with pytest.raises(ValueError):
        ask_pipeline(str(tmp_path), [], llm=fake_llm)


def test_change_collector_dedup_and_drain():
    c = ChangeCollector()
    c.add("/x/a.pdf")
    c.add("/x/b.pdf")
    c.add("/x/a.pdf")
    paths, last = c.pending()
    assert paths == ["/x/a.pdf", "/x/b.pdf"]
    assert last > 0
    assert len(c) == 2
    assert c.drain() == ["/x/a.pdf", "/x/b.pdf"]
    assert len(c) == 0


def test_organize_once_applies_pipeline(tmp_path):
    (tmp_path / "报告.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "照片.jpg").write_text("jpg", encoding="utf-8")
    desc = {"stages": [{"op": "classify", "by": "type"}, {"op": "move", "rule": "by_category"}]}
    out = organize_once(str(tmp_path), desc)
    assert out["result"]["summary"]["applied"] == 2
    assert (tmp_path / "文档" / "报告.pdf").exists()
    assert (tmp_path / "图片" / "照片.jpg").exists()
