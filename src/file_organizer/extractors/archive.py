"""ZIP 内容摘要抽取（标准库 zipfile，无额外依赖）。

只列出条目名（含目录结构），用于按压缩包内容主题分类。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

MAX_ENTRIES = 60


def extract_zip_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """列出 ZIP 内条目名作为内容摘要。损坏/加密时返回空串。"""
    try:
        with zipfile.ZipFile(str(path)) as zf:
            names = zf.namelist()
    except Exception:
        return ""
    return " ".join(names[:MAX_ENTRIES])[:max_chars]
