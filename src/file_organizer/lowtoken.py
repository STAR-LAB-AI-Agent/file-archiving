"""面向模型的紧凑摘要：token 估算 + 计划摘要。"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文约 1 字≈1 token，其余约 4 字符≈1 token。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = len(text) - cjk
    return cjk + other // 4 + (1 if other % 4 else 0)


def summarize_plan_for_llm(plan: dict, *, max_actions: int = 5) -> str:
    """把完整计划压缩为面向模型的简短摘要（只给计数 + 前几条动作）。"""
    s = plan["summary"]
    lines = [
        f"计划共 {s['total']} 项：移动 {s['to_move']}，重命名 {s['to_rename']}，"
        f"移动并重命名 {s['to_move_and_rename']}，跳过 {s['skip']}，冲突 {s['conflicts']}。"
    ]
    for a in plan["actions"][:max_actions]:
        lines.append(f"- {a['op']}: {a['source']} -> {a['target']}")
    if len(plan["actions"]) > max_actions:
        lines.append(f"... 其余 {len(plan['actions']) - max_actions} 项省略")
    return "\n".join(lines)
