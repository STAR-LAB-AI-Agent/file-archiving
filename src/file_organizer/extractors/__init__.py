"""内容抽取：从各类文件抽取文本摘要（限长），供 classify(by=content) 使用。

原则：只抽前 max_chars 字符，避免整文进入模型上下文。
PDF / DOCX 依赖可选第三方库（pypdf / python-docx），未安装时优雅降级为空串。
"""

from __future__ import annotations

from pathlib import Path

# 可直接按文本读取的扩展名
TEXT_SUFFIXES = {
    ".txt", ".md", ".csv", ".json", ".log",
    ".py", ".js", ".ts", ".html", ".xml", ".yaml", ".yml",
}

DEFAULT_MAX_CHARS = 512


def extract_text(path: str | Path, *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """抽取文件文本摘要（截断到 max_chars 字符）。失败/不支持时返回空串。"""
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        if suffix in TEXT_SUFFIXES:
            text = p.read_text(encoding="utf-8", errors="ignore")
        elif suffix == ".pdf":
            text = _extract_pdf(p)
        elif suffix == ".docx":
            text = _extract_docx(p)
        else:
            text = ""
    except Exception:
        text = ""
    return text[:max_chars]


def _extract_pdf(p: Path) -> str:
    try:
        from .pdf import extract_pdf_text
        return extract_pdf_text(p)
    except ImportError:
        return ""


def _extract_docx(p: Path) -> str:
    try:
        from .docx import extract_docx_text
        return extract_docx_text(p)
    except ImportError:
        return ""
