"""低 Token 工具单测。"""

from file_organizer.lowtoken import estimate_tokens, summarize_plan_for_llm


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("你好") == 2  # 2 个中文
    assert estimate_tokens("abcd") == 1  # 4 字符 ≈ 1 token


def test_summarize_plan_for_llm():
    plan = {
        "summary": {"total": 10, "to_move": 8, "to_rename": 2, "to_move_and_rename": 0, "skip": 0, "conflicts": 1},
        "actions": [{"op": "move", "source": "s", "target": "t"} for _ in range(10)],
    }
    text = summarize_plan_for_llm(plan, max_actions=3)
    assert "计划共 10 项" in text
    assert "其余 7 项省略" in text
    assert len(text) < len(str(plan))
