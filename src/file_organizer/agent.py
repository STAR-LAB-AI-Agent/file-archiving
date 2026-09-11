"""意图识别入口：把自然语言翻译为声明式 pipeline，复用 scan→pipeline→plan→apply 全链路。

用「规则匹配 + 槽位抽取」解析意图，无需外部 LLM 即可跑通。
parse_intent 可替换为任意 LLM / function-calling 实现，其余链路保持不变。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .executor import apply_plan
from .lowtoken import estimate_tokens, summarize_plan_for_llm
from .pipeline import DEFAULT_PIPELINE, apply_options, run_pipeline
from .planner import build_plan, render_preview
from .scanner import scan_directory
from .security import assert_safe_root

log = logging.getLogger(__name__)


class AgentError(ValueError):
    """意图理解 / 参数缺失错误。"""


def _extract_template(text: str) -> str | None:
    m = re.search(r"(?:重命名|改名|命名)(?:为|成)?\s*[:：]?\s*(?P<t>[^\s，。；]+)", text)
    return m.group("t") if m else None


def _extract_target(text: str) -> str | None:
    m = re.search(r"(?:移到|移动(?:到)?|归档(?:到)?|放到)\s*[:：]?\s*(?P<t>[^\s，。；]+)", text)
    return m.group("t") if m else None


def _extract_dimension(text: str) -> str:
    if "内容" in text:
        return "content"
    if "文件名" in text or "名字" in text:
        return "name"
    return "type"


def parse_intent(text: str) -> dict:
    """自然语言 → 结构化意图 {"name", "params"}。"""
    t = (text or "").strip()
    if not t:
        raise AgentError("指令为空，请描述要如何整理文件。")

    if any(k in t for k in ("重命名", "改名", "命名")):
        return {"name": "rename", "params": {"template": _extract_template(t)}}
    if any(k in t for k in ("监听", "自动整理", "自动归类")):
        return {"name": "watch", "params": {}}
    if any(k in t for k in ("去重", "重复", "查重")):
        return {"name": "dedup", "params": {}}
    if any(k in t for k in ("移动", "移到", "归档", "放到", "移走")):
        return {"name": "move", "params": {"target": _extract_target(t)}}
    # 注意：organize 需在 classify 之前判断，避免"按类型整理"被误判为 classify
    if any(k in t for k in ("整理", "归纳", "收拾", "规整")):
        return {"name": "organize", "params": {}}
    if any(k in t for k in ("分类", "归类", "按类型", "按内容", "按文件名")):
        return {"name": "classify", "params": {"by": _extract_dimension(t)}}

    raise AgentError(f"无法理解的指令: {text!r}，可尝试：整理 / 分类 / 重命名 / 移动 / 归档。")


def build_pipeline(intent: dict) -> dict:
    """意图 → 声明式 pipeline 描述。"""
    name = intent["name"]
    params = intent.get("params", {})

    if name == "organize":
        return dict(DEFAULT_PIPELINE)
    if name == "classify":
        return {"stages": [
            {"op": "classify", "by": params.get("by", "type")},
            {"op": "move", "rule": "by_category"},
        ]}
    if name == "rename":
        template = params.get("template")
        if not template:
            raise AgentError("重命名需要模板，例如：重命名为 {date}_{index:03d}{suffix}")
        return {"stages": [{"op": "rename", "template": template}]}
    if name == "move":
        target = params.get("target")
        if target:
            return {"stages": [{"op": "move", "rule": "to_path", "target": target}]}
        return {"stages": [
            {"op": "classify", "by": "type"},
            {"op": "move", "rule": "by_category"},
        ]}
    if name == "dedup":
        return {"stages": [
            {"op": "dedup", "by": "content_hash", "keep": "first"},
            {"op": "filter", "where": {"field": "is_kept", "op": "eq", "value": False}},
            {"op": "move", "rule": "to_path", "target": "重复文件"},
        ]}
    if name == "watch":
        raise AgentError("watch（自动监听）尚未实现。")
    raise AgentError(f"未知意图: {name}")


def run_instruction(
    text: str,
    path: str,
    *,
    execute: bool = False,
    conflict_policy: str = "skip",
    rules=None,
    preserve: bool = False,
) -> dict:
    """端到端：自然语言 → 意图 → 管道 → 扫描 → 计划 →（可选）执行。

    execute=False 仅生成计划/预览（不落盘）；execute=True 生成计划后立即落盘。
    rules：传给 apply_options 的内容分类规则来源（None/dict/JSON/YAML 路径）。
    preserve：True 时 move 就地分类，保留嵌套结构。
    返回包含 instruction / intent / pipeline / plan / preview / result 的字典。
    """
    intent = parse_intent(text)
    pipeline = build_pipeline(intent)
    pipeline = apply_options(pipeline, rules=rules, preserve=preserve)
    root = str(Path(path).expanduser().resolve())
    assert_safe_root(root)  # 安全：拒绝操作系统目录

    result = scan_directory(root)
    entries = run_pipeline(pipeline, result.entries, root=root)
    plan = build_plan(entries, root=root)

    summary_for_llm = summarize_plan_for_llm(plan)
    out: dict = {
        "instruction": text,
        "intent": intent,
        "pipeline": pipeline,
        "plan": plan,
        "preview": render_preview(plan),
        "llm_summary": summary_for_llm,
        "token_estimate": {
            "preview_tokens": estimate_tokens(render_preview(plan)),
            "summary_tokens": estimate_tokens(summary_for_llm),
        },
        "result": None,
    }
    if execute:
        out["result"] = apply_plan(plan, conflict_policy=conflict_policy)
    log.info("指令执行 intent=%s execute=%s", intent["name"], execute)
    return out
