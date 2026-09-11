"""DOCX 文本抽取（可选依赖 python-docx）。"""

from __future__ import annotations

from pathlib import Path


def extract_docx_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """使用 python-docx 抽取 DOCX 段落文本，截断到 max_chars。未安装时抛 ImportError。"""
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError("DOCX 抽取需要 python-docx：pip install python-docx") from exc

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)[:max_chars]
