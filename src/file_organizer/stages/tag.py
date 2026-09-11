"""tag 原语：给匹配记录打标签（写入 tags，不落盘）。"""

from __future__ import annotations

from ..model import FileRecord
from .where import matches


def tag_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """打标签。params.tags 为标签或标签列表；params.where 可选（仅对匹配项）。"""
    tags = params.get("tags")
    if not tags:
        raise ValueError("tag 需要 tags 参数（字符串或列表）")
    if isinstance(tags, str):
        tags = [tags]
    where = params.get("where")

    for e in entries:
        if matches(e, where):
            for t in tags:
                if t not in e.tags:
                    e.tags.append(t)
    return entries
