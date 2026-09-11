"""一键撤销：按 history 栈逆向恢复最近 N 次整理。"""

from __future__ import annotations

import json
from pathlib import Path


def _history_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve() / ".file_organizer" / "undo_history.json"


def undo_history(path) -> list:
    """读取撤销历史（按时间正序的 session 列表）。"""
    p = _history_path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _cleanup_empty_dirs(root: Path, dirs) -> None:
    """清理撤销后变空的目录（从深到浅沿父链向上，不删 root 与 .file_organizer）。"""
    candidates = sorted({Path(d) for d in dirs if d is not None}, key=lambda p: len(p.parts), reverse=True)
    for d in candidates:
        cur = d
        while cur != root and cur.name != ".file_organizer":
            try:
                if cur.is_dir() and not any(cur.iterdir()):
                    cur.rmdir()
                else:
                    break
            except OSError:
                break
            cur = cur.parent


def undo_last(path, *, n: int = 1) -> dict:
    """撤销最近 n 次整理（逆向恢复），清理空目录，并从历史中移除已撤销项。

    返回 {"undone": N, "failed": [...], "remaining_sessions": N}。
    """
    root = Path(path).expanduser().resolve()
    log_path = _history_path(path)
    history = undo_history(path)
    if not history:
        return {"undone": 0, "failed": [], "remaining_sessions": 0}

    n = max(1, min(n, len(history)))
    sessions = history[-n:]
    undone: list[dict] = []
    failed: list[dict] = []
    emptied: set[Path] = set()

    # 后进的 session 先撤销；同一 session 内倒序恢复，避免目标重叠
    for session in reversed(sessions):
        for entry in reversed(session.get("entries", [])):
            target = Path(entry["target"])
            source = Path(entry["source"])
            try:
                if target.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    target.rename(source)
                    undone.append({"source": str(source), "target": str(target), "op": entry.get("op")})
                    emptied.add(target.parent)
                else:
                    failed.append({**entry, "reason": "目标不存在，可能已被移动"})
            except OSError as exc:
                failed.append({**entry, "reason": str(exc)})

    _cleanup_empty_dirs(root, emptied)

    remaining = history[:-n]
    log_path.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"undone": len(undone), "failed": failed, "remaining_sessions": len(remaining)}
