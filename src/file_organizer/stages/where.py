"""条件表达式（where）求值器。

语法：
    where := {"field","op","value"} | {"and":[where...]} | {"or":[where...]} | {"not": where}
    field ∈ {name, stem, suffix, extension, mime_type, size, mtime, mtime_days,
             category, tags, dup_group, is_kept, relative_path, new_name, target}
    op    ∈ {eq, ne, in, not_in, gt, gte, lt, lte, contains, startswith, endswith, regex}
"""

from __future__ import annotations

import re

from ..model import FileRecord


class StageError(ValueError):
    """原语 / 管道错误。"""


_FIELDS = {
    "name", "stem", "suffix", "extension", "mime_type",
    "size", "mtime", "mtime_days", "category", "tags", "dup_group", "is_kept",
    "relative_path", "new_name", "target",
}


def _get(record: FileRecord, field: str):
    if field not in _FIELDS:
        raise StageError(f"未知字段: {field}")
    return getattr(record, field)


def _compare(actual, op: str, value) -> bool:
    if op == "eq":
        return actual == value
    if op == "ne":
        return actual != value
    if op == "in":
        return actual in value
    if op == "not_in":
        return actual not in value
    if op == "gt":
        return actual > value
    if op == "gte":
        return actual >= value
    if op == "lt":
        return actual < value
    if op == "lte":
        return actual <= value
    if op == "contains":
        return value in (actual or "")
    if op == "startswith":
        return (actual or "").startswith(value)
    if op == "endswith":
        return (actual or "").endswith(value)
    if op == "regex":
        return re.search(value, actual or "") is not None
    raise StageError(f"未知操作符: {op}")


def matches(record: FileRecord, where: dict | None) -> bool:
    """判断记录是否满足 where 条件；where 为 None 表示全部满足。"""
    if where is None:
        return True
    if "and" in where:
        return all(matches(record, w) for w in where["and"])
    if "or" in where:
        return any(matches(record, w) for w in where["or"])
    if "not" in where:
        return not matches(record, where["not"])
    if "field" not in where or "op" not in where:
        raise StageError(f"条件缺少 field/op: {where}")
    return _compare(_get(record, where["field"]), where["op"], where["value"])
