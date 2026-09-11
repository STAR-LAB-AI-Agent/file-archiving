"""planner：把 stage 变换后的记录汇总为可预览的 plan.json，并做冲突检测。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .model import FileRecord


def build_plan(entries: list[FileRecord], *, root: str) -> dict:
    """根据记录的 target/new_name 生成执行计划（plan.json），不落盘。

    返回结构见 §3.5：session_id / created_at / root / summary / actions。
    冲突检测：目标路径已存在、多个记录指向同一目标。
    """
    actions: list[dict] = []
    seen_targets: dict[str, str] = {}  # target 绝对路径 -> 首个 action id
    conflict_count = 0
    count = {"move": 0, "rename": 0, "move_and_rename": 0, "skip": 0}

    for i, e in enumerate(entries):
        source = Path(e.path)
        target_dir = Path(e.target) if e.target else source.parent
        final_name = e.new_name or e.name
        target = target_dir / final_name

        # 无操作：目标等于源
        if str(target) == str(source):
            count["skip"] += 1
            continue

        same_dir = target.parent == source.parent
        same_name = target.name == source.name
        if same_dir and not same_name:
            op = "rename"
        elif not same_dir and same_name:
            op = "move"
        else:
            op = "move_and_rename"
        count[op] += 1

        action: dict = {
            "id": f"a{i:03d}",
            "op": op,
            "source": str(source),
            "target": str(target),
            "rename_from": e.name if not same_name else None,
            "rename_to": final_name if not same_name else None,
            "reason": _reason(e, op),
            "risk": "medium",
            "conflict": None,
            "external_target": bool(e.external_target),
        }

        key = str(target)
        if key in seen_targets:
            action["conflict"] = f"目标重复：与 {seen_targets[key]} 指向同一路径"
            conflict_count += 1
        elif target.exists():
            action["conflict"] = "目标已存在"
            conflict_count += 1
        else:
            seen_targets[key] = action["id"]

        actions.append(action)

    return {
        "session_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(Path(root)),
        "summary": {
            "total": len(entries),
            "to_move": count["move"],
            "to_rename": count["rename"],
            "to_move_and_rename": count["move_and_rename"],
            "skip": count["skip"],
            "conflicts": conflict_count,
        },
        "actions": actions,
    }


def _reason(e: FileRecord, op: str) -> str:
    if op == "rename":
        return f"重命名: {e.name} → {e.new_name}"
    if op == "move":
        return f"移动: 分类={e.category or '未分类'}"
    return f"移动并重命名: {e.name} → {e.new_name}，分类={e.category or '未分类'}"


def render_preview(plan: dict) -> str:
    """把计划渲染为人类可读的预览文本。"""
    s = plan["summary"]
    lines = [
        f"计划预览  session={plan['session_id']}  root={plan['root']}",
        f"共 {s['total']} 个文件 | 移动 {s['to_move']} | 重命名 {s['to_rename']} | "
        f"移动并重命名 {s['to_move_and_rename']} | 跳过 {s['skip']} | 冲突 {s['conflicts']}",
        "-" * 100,
    ]
    for a in plan["actions"]:
        flag = f"  ⚠ {a['conflict']}" if a["conflict"] else ""
        lines.append(f"[{a['op']:<14}] {a['source']}  ->  {a['target']}{flag}")
    return "\n".join(lines)
