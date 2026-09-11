"""theme LLM 内容主题发现单测（不真正调用大模型，用注入的 fake llm）。"""

from file_organizer.theme import (
    build_user_prompt,
    discover_content_rules,
    parse_rules_json,
    sample_files,
)


def test_parse_rules_json_plain():
    rules = parse_rules_json('{"团委": ["团委", "共青团"], "舞台剧": ["舞台剧", "排练"]}')
    assert rules == {"团委": ["团委", "共青团"], "舞台剧": ["舞台剧", "排练"]}


def test_parse_rules_json_code_fence():
    raw = '```json\n{"A": ["a"], "B": ["b"]}\n```'
    assert parse_rules_json(raw) == {"A": ["a"], "B": ["b"]}


def test_build_user_prompt():
    samples = [("a.txt", "hello"), ("b.txt", "world")]
    prompt = build_user_prompt(samples)
    assert "a.txt" in prompt and "hello" in prompt
    assert "b.txt" in prompt and "world" in prompt


def test_sample_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "b.jpg").write_text("not extractable", encoding="utf-8")
    samples = sample_files(str(tmp_path), max_files=5, max_chars=100)
    rels = [rel for rel, _ in samples]
    assert "a.txt" in rels
    assert "b.jpg" not in rels  # 图片不可抽取文本，被跳过


def test_discover_content_rules_with_fake_llm(tmp_path):
    (tmp_path / "a.txt").write_text("团委述职报告", encoding="utf-8")
    (tmp_path / "b.txt").write_text("舞台剧排练", encoding="utf-8")

    def fake_llm(system, user):
        return '{"团委": ["团委", "述职"], "舞台剧": ["舞台剧", "排练"]}'

    rules = discover_content_rules(str(tmp_path), llm=fake_llm)
    assert rules == {"团委": ["团委", "述职"], "舞台剧": ["舞台剧", "排练"]}
