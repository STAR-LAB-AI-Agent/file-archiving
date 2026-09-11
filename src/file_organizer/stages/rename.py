"""rename 原语：按模板生成新文件名（写入 new_name，不落盘）。

模板占位符：
    {date}     修改日期 YYYY-MM-DD
    {time}     修改时间 HHMMSS
    {stem}     原文件名（去扩展名）
    {name}     原文件名（含扩展名）
    {suffix}   扩展名（含点，如 ".jpg"）
    {ext}      扩展名（不含点，如 "jpg"）
    {category} 分类名（未分类为空串）
    {index}    序号（可格式化，如 {index:03d}）
"""

from __future__ import annotations

from datetime import datetime

from ..model import FileRecord
from .where import matches


def rename_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """重命名。params.template 必填；params.where 可选（仅重命名匹配项）；
    params.index_start 为起始序号（默认 1）。
    """
    template = params.get("template")
    if not template:
        raise ValueError("rename 需要 template 参数")
    where = params.get("where")
    index = int(params.get("index_start", 1))

    for e in entries:
        if not matches(e, where):
            continue
        values = _render_values(e, index)
        e.new_name = template.format(**values)
        index += 1
    return entries


def _safe_datetime(mtime: float) -> datetime:
    """把 mtime 安全转为本地 datetime；无效值（-1/0/超范围）回退到 epoch，避免崩溃。"""
    try:
        return datetime.fromtimestamp(mtime)
    except (OSError, ValueError, OverflowError):
        return datetime(1970, 1, 1)


def _render_values(e: FileRecord, index: int) -> dict:
    dt = _safe_datetime(e.mtime)
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H%M%S"),
        "stem": e.stem,
        "name": e.name,
        "suffix": e.suffix,
        "ext": e.extension,
        "category": e.category or "",
        "index": index,
    }
