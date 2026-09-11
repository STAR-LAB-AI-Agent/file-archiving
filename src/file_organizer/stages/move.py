"""move 原语：计算目标目录（写入 target，不落盘）。"""

from __future__ import annotations

from pathlib import Path

from ..model import FileRecord
from ..rules import DEFAULT_FOLDER
from .where import StageError, matches


def move_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """移动。params.rule ∈ {by_category, to_path}。

    - by_category：目标目录 = root / 分类名（未分类用默认目录）；
      设置 params.preserve=True 时改为「就地分类」：目标 = 文件所在目录 / 分类名，
      保留原有嵌套结构（幂等：已在该分类目录下则原地不动）。
    - to_path：目标目录 = params.target（相对路径则基于 root 解析）
    params.where 可选，仅对匹配记录计算目标。
    """
    rule = params.get("rule", "by_category")
    where = params.get("where")
    root = ctx.get("root")

    if rule == "by_category":
        if not root:
            raise StageError("move by_category 需要 ctx['root']")
        default = ctx.get("rules", {}).get("default_folder", DEFAULT_FOLDER)
        preserve = bool(params.get("preserve", False))
        for e in entries:
            if matches(e, where):
                category = e.category or default
                if preserve:
                    e.target = _inplace_target(e, category)
                else:
                    e.target = str(Path(root) / category)
    elif rule == "to_path":
        target = params.get("target")
        if not target:
            raise StageError("move to_path 需要 target 参数")
        target_dir = _resolve_dir(target, root)
        external = Path(target).is_absolute()  # 显式绝对路径目标：允许跨出根目录
        for e in entries:
            if matches(e, where):
                e.target = target_dir
                e.external_target = external
    else:
        raise StageError(f"未知 move 规则: {rule}")
    return entries


def _resolve_dir(target: str, root: str | None) -> str:
    p = Path(target)
    if not p.is_absolute() and root:
        p = Path(root) / p
    return str(p)


def _inplace_target(e: FileRecord, category: str) -> str:
    """就地分类目标：文件所在目录 / 分类名（保留嵌套结构，避免扁平化）。"""
    parent = Path(e.path).parent
    cat_name = Path(category).name
    if cat_name and parent.name == cat_name:
        return str(parent)  # 已就位，避免 文档/文档 二次嵌套
    return str(parent / category)
