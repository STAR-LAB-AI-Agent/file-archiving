"""LLM 驱动的内容主题发现：从目录采样文本，让大模型归纳「主题 → 关键词」规则。

与 classify(by=content) 解耦：本模块只负责「发现规则」，classify 负责「应用规则」。
使内容分类不再依赖写死的 DEFAULT_CONTENT_RULES，而是适配任意目录的真实内容。
"""

from __future__ import annotations

import json
from pathlib import Path

from .extractors import extract_text
from .scanner import scan_directory

SYSTEM_PROMPT = (
    "你是文件内容分类规则提取器。下面给出一个目录里若干文件的文本摘要（文件名 + 内容片段）。"
    "请归纳出 3～8 个内容主题分类，每个主题给出若干中文关键词（用于后续子串匹配）。"
    "只输出一个 JSON 对象，格式：{\"主题名\": [\"关键词1\", \"关键词2\", ...]}。"
    "关键词应具有区分度，避免过宽泛的词。不要输出任何解释或 markdown 代码块。"
)


def sample_files(path, *, max_files: int = 15, max_chars: int = 400) -> list[tuple[str, str]]:
    """扫描目录，抽取可读文本的文件样本（限数量与长度）。返回 [(相对路径, 摘要)]。"""
    root = str(Path(path).expanduser().resolve())
    result = scan_directory(root)
    samples: list[tuple[str, str]] = []
    for e in result.entries:
        text = extract_text(e.path, max_chars=max_chars).strip()
        if text:
            samples.append((e.relative_path, text))
            if len(samples) >= max_files:
                break
    return samples


def build_user_prompt(samples) -> str:
    lines = []
    for rel, text in samples:
        lines.append(f"--- 文件：{rel} ---\n{text}")
    return "\n\n".join(lines)


def parse_rules_json(raw: str) -> dict:
    """把 LLM 返回的文本解析为 {主题: [关键词...]}。"""
    t = raw.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        t = t.strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    obj = json.loads(t)
    return {k: v for k, v in obj.items() if isinstance(v, list)}


def discover_content_rules(path, *, llm=None, max_files: int = 15, max_chars: int = 400) -> dict:
    """采样目录内容，调用 LLM 归纳内容分类规则。返回 {主题: [关键词...]}。

    llm 可为 callable(system, user) -> str，便于测试注入；缺省用 llm.chat。
    """
    samples = sample_files(path, max_files=max_files, max_chars=max_chars)
    if not samples:
        return {}
    if llm is None:
        from .llm import chat

        def _chat(system: str, user: str) -> str:
            return chat(system, user)

        llm = _chat
    raw = llm(SYSTEM_PROMPT, build_user_prompt(samples))
    return parse_rules_json(raw)
