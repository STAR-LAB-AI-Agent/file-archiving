"""sort 原语：排序（影响后续 rename 的序号顺序，不落盘）。"""

from __future__ import annotations

from ..model import FileRecord
from .where import StageError


def sort_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """排序。params.by ∈ {name, relative_path, size, mtime, type, category}；
    params.order ∈ {asc, desc}，默认 asc。
    """
    by = params.get("by", "name")
    reverse = params.get("order", "asc") == "desc"

    key_fns = {
        "name": lambda e: e.name.lower(),
        "relative_path": lambda e: e.relative_path.lower(),
        "size": lambda e: e.size,
        "mtime": lambda e: e.mtime,
        "type": lambda e: (e.extension, e.name.lower()),
        "category": lambda e: (e.category or "", e.name.lower()),
    }
    if by not in key_fns:
        raise StageError(f"未知排序字段: {by}")
    return sorted(entries, key=key_fns[by], reverse=reverse)
