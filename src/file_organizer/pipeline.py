"""声明式管道：按 pipeline 描述顺序执行可组合原语（stage）。"""

from __future__ import annotations

import json
from pathlib import Path

from .model import FileRecord
from .stages import STAGE_REGISTRY
from .stages.where import StageError

# 默认管道 = 「一键全流程整理」：按类型分类 → 移动到分类子目录
DEFAULT_PIPELINE: dict = {
    "stages": [
        {"op": "classify", "by": "type"},
        {"op": "move", "rule": "by_category"},
    ]
}


def run_pipeline(
    desc: dict,
    entries: list[FileRecord],
    *,
    root: str | None = None,
) -> list[FileRecord]:
    """按 desc["stages"] 顺序依次执行各原语，返回变换后的记录列表。

    desc 结构：
        {"root": "...", "rules": {...}, "stages": [{"op": "filter", ...}, ...]}
    """
    ctx = {
        "root": root or desc.get("root"),
        "rules": desc.get("rules", {}),
    }
    for s in desc.get("stages", []):
        op = s.get("op")
        if op not in STAGE_REGISTRY:
            raise StageError(f"未知 stage: {op}")
        entries = STAGE_REGISTRY[op](entries, s, ctx)
    return entries


def load_pipeline(source) -> dict:
    """加载管道描述。

    - None → 默认管道
    - dict → 原样返回
    - str/Path → 视为 pipeline JSON 文件路径读取
    """
    if source is None:
        return DEFAULT_PIPELINE
    if isinstance(source, dict):
        return source
    if isinstance(source, (str, Path)):
        return json.loads(Path(source).read_text(encoding="utf-8"))
    raise TypeError(f"不支持的 pipeline 来源: {type(source)}")


def apply_options(desc: dict, *, rules=None, preserve: bool = False) -> dict:
    """把规则来源与「就地移动」选项注入 pipeline 描述（返回新 dict，不改原 desc）。

    - rules：传给 load_rules 的规则来源（None=不覆盖 / dict / JSON/YAML 路径）。
    - preserve=True：给所有 move stage 追加 preserve=True（就地分类，保留嵌套结构）。
    """
    d = dict(desc)
    if rules is not None:
        from .rules import load_rules

        d["rules"] = load_rules(rules)
    if preserve:
        d["stages"] = [
            {**s, "preserve": True} if s.get("op") == "move" else s
            for s in d.get("stages", [])
        ]
    return d
