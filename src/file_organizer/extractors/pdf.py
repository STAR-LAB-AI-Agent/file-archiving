"""PDF 文本抽取（可选依赖 pypdf）。"""

from __future__ import annotations

from pathlib import Path


def extract_pdf_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """使用 pypdf 抽取 PDF 全文，截断到 max_chars。未安装 pypdf 时抛 ImportError。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("PDF 抽取需要 pypdf：pip install -e '.[content]'") from exc

    reader = PdfReader(str(path))
    parts: list[str] = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
        total += len(text)
        if total >= max_chars:
            break  # 抽够摘要即停，避免解析整本大 PDF
    return "\n".join(parts)[:max_chars]
