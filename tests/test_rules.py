"""rules 规则加载单测。"""

from file_organizer.rules import DEFAULT_CONTENT_RULES, DEFAULT_FOLDER, load_rules


def test_load_rules_none_returns_defaults():
    r = load_rules()
    assert r["content_rules"] == DEFAULT_CONTENT_RULES
    assert r["default_folder"] == DEFAULT_FOLDER


def test_load_rules_dict_merges_with_defaults():
    r = load_rules({"content_rules": {"自定义": ["词"]}})
    assert r["content_rules"] == {"自定义": ["词"]}
    assert r["default_folder"] == DEFAULT_FOLDER  # 缺失键用默认


def test_load_rules_json_file(tmp_path):
    p = tmp_path / "rules.json"
    p.write_text('{"content_rules": {"团委": ["团委", "共青团"]}}', encoding="utf-8")
    r = load_rules(p)
    assert r["content_rules"] == {"团委": ["团委", "共青团"]}
    assert r["default_folder"] == DEFAULT_FOLDER
