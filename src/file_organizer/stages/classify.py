"""classify 原语：按维度写入 category（不落盘）。"""

from __future__ import annotations

from ..extractors import extract_text
from ..model import FileRecord
from ..rules import DEFAULT_CONTENT_RULES, DEFAULT_FOLDER, DEFAULT_NAME_RULES, DEFAULT_TYPE_RULES
from .where import StageError, matches


def classify_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """分类。params.by ∈ {type, name, content}；params.mode ∈ {overwrite, append}。

    - type：按扩展名规则（ctx.rules.type_rules）
    - name：按文件名关键词规则（ctx.rules.name_rules）
    - content：抽取文本摘要，按内容关键词规则（ctx.rules.content_rules）
    - mode="overwrite"（默认）：覆盖 category
    - mode="append"：在已有 category 后追加，形成层级分类（如 合同/文档）
    params.where 可选，仅对满足条件的记录分类。
    """
    by = params.get("by", "type")
    mode = params.get("mode", "overwrite")
    rules = ctx.get("rules", {})
    where = params.get("where")

    if by == "type":
        type_rules = rules.get("type_rules", DEFAULT_TYPE_RULES)
        default = rules.get("default_folder", DEFAULT_FOLDER)
        for e in entries:
            if matches(e, where):
                e.category = _combine(e.category, _category_by_type(e.extension, type_rules, default), mode)
    elif by == "name":
        name_rules = rules.get("name_rules", DEFAULT_NAME_RULES)
        default = rules.get("default_folder", DEFAULT_FOLDER)
        for e in entries:
            if matches(e, where):
                e.category = _combine(e.category, _category_by_name(e.name, name_rules, default), mode)
    elif by == "content":
        content_rules = rules.get("content_rules", DEFAULT_CONTENT_RULES)
        default = rules.get("default_folder", DEFAULT_FOLDER)
        for e in entries:
            if matches(e, where):
                text = extract_text(e.path)  # 默认限长 512 字符
                e.category = _combine(e.category, _category_by_content(text, content_rules, default), mode)
    else:
        raise StageError(f"未知分类维度: {by}")
    return entries


def _combine(current: str | None, value: str, mode: str) -> str:
    """按 mode 合并分类：overwrite 覆盖；append 追加为层级路径（当前/新值）。"""
    if mode == "append" and current:
        return f"{current}/{value}"
    return value


def _category_by_type(extension: str, type_rules: dict, default: str) -> str:
    for category, exts in type_rules.items():
        if extension in exts:
            return category
    return default


def _category_by_name(name: str, name_rules: dict, default: str) -> str:
    for category, keywords in name_rules.items():
        if any(k in name for k in keywords):
            return category
    return default


def _category_by_content(text: str, content_rules: dict, default: str) -> str:
    lowered = (text or "").lower()
    for category, keywords in content_rules.items():
        if any(k.lower() in lowered for k in keywords):
            return category
    return default
