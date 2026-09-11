"""executor：执行 plan（真正落盘），记录撤销映射（undo_log），并做越界安全检查。"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from .security import is_within
from .stages.where import StageError

log = logging.getLogger(__name__)


def apply_plan(
    plan: dict,
    *,
    conflict_policy: str = "skip",
    dry_run: bool = False,
    only: set[str] | None = None,
    exclude: set[str] | None = None,
) -> dict:
    """执行 plan 中的动作。

    conflict_policy:
        - skip          存在冲突的动作跳过（默认，最安全）
        - overwrite     覆盖已存在的目标
        - rename_suffix 目标已存在时追加 " (1)" 后缀
    only / exclude：按 action id 选择性执行。
    dry_run=True 时不落盘，仅返回将要执行的清单。
    """
    if conflict_policy not in ("skip", "overwrite", "rename_suffix"):
        raise StageError(f"未知冲突策略: {conflict_policy}")

    root = plan.get("root")
    applied: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []

    for action in plan["actions"]:
        # 选择性执行
        if only is not None and action["id"] not in only:
            skipped.append({**action, "reason": "未在 --only 列表"})
            continue
        if exclude is not None and action["id"] in exclude:
            skipped.append({**action, "reason": "被 --exclude 排除"})
            continue

        source = Path(action["source"])
        target = Path(action["target"])

        # 安全：目标必须位于整理根目录内（越界拒绝）；显式绝对路径目标（to_path）除外
        if root and not action.get("external_target") and not is_within(target, root):
            failed.append({**action, "reason": "越界拒绝：目标超出整理根目录"})
            continue

        # 冲突处理
        if action.get("conflict"):
            if conflict_policy == "skip":
                skipped.append({**action, "reason": f"冲突跳过: {action['conflict']}"})
                continue
            if conflict_policy == "rename_suffix":
                target = _suffix_target(target)
                action["target"] = str(target)
                action["conflict"] = None
            # overwrite 策略：走到下方，先删除已存在目标再重命名

        if dry_run:
            skipped.append({**action, "reason": "dry-run 未执行"})
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if conflict_policy == "overwrite" and target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            source.rename(target)
            applied.append({"source": str(source), "target": str(target), "op": action["op"]})
        except OSError as exc:
            failed.append({**action, "reason": str(exc)})

    result = {
        "session_id": plan.get("session_id"),
        "summary": {
            "applied": len(applied),
            "skipped": len(skipped),
            "failed": len(failed),
        },
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
    }
    log.info(
        "apply 完成 session=%s applied=%d skipped=%d failed=%d",
        plan.get("session_id"), len(applied), len(skipped), len(failed),
    )
    _append_undo_log(plan, applied)
    return result


def _suffix_target(target: Path) -> Path:
    """为已存在的目标生成 " (1)"、" (2)"... 的不冲突路径。"""
    if not target.exists():
        return target
    i = 1
    while True:
        cand = target.with_name(f"{target.stem} ({i}){target.suffix}")
        if not cand.exists():
            return cand
        i += 1


def _append_undo_log(plan: dict, applied: list[dict]) -> None:
    """把本次成功动作追加到撤销历史（undo 命令读取它）。"""
    if not applied:
        return
    root = Path(plan.get("root", "."))
    log_dir = root / ".file_organizer"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "undo_history.json"

    history: list = []
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.append({
        "session_id": plan.get("session_id"),
        "applied_at": plan.get("created_at"),
        "entries": applied,
    })
    log_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
