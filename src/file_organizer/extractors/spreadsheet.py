"""XLSX / XLS 文本抽取（可选依赖 openpyxl / xlrd）。

只抽前若干行、若干列，够做内容分类即可。
"""

from __future__ import annotations

from pathlib import Path

MAX_ROWS = 12
MAX_COLS = 10


def extract_xlsx_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """使用 openpyxl 抽取 XLSX 单元格文本。未安装时抛 ImportError。"""
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError("XLSX 抽取需要 openpyxl：pip install openpyxl") from exc

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    parts: list[str] = []
    try:
        for ws in wb.worksheets:
            parts.append(ws.title)
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= MAX_ROWS:
                    break
                cells = [str(v) for v in row[:MAX_COLS] if v is not None]
                if cells:
                    parts.append(" ".join(cells))
    finally:
        wb.close()
    return "\n".join(parts)[:max_chars]


def extract_xls_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """使用 xlrd 抽取 XLS 单元格文本。未安装时抛 ImportError。"""
    try:
        import xlrd
    except ImportError as exc:
        raise ImportError("XLS 抽取需要 xlrd：pip install xlrd") from exc

    wb = xlrd.open_workbook(str(path))
    parts: list[str] = []
    for sh in wb.sheets():
        parts.append(sh.name)
        for r in range(min(sh.nrows, MAX_ROWS)):
            cells = [
                str(sh.cell_value(r, c))
                for c in range(min(sh.ncols, MAX_COLS))
                if str(sh.cell_value(r, c)).strip()
            ]
            if cells:
                parts.append(" ".join(cells))
    return "\n".join(parts)[:max_chars]
