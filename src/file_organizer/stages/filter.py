"""filter 原语：按条件筛选，返回匹配的子集（不落盘）。"""

from __future__ import annotations

from ..model import FileRecord
from .where import matches


def filter_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """筛选。params.where 为条件表达式；where 缺省则全部保留。"""
    where = params.get("where")
    return [e for e in entries if matches(e, where)]
