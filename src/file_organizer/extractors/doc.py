"""DOC（Word 97-2003 二进制格式）文本抽取。

不依赖 antiword/LibreOffice：直接解析 OLE 复合文档的 WordDocument 流，
按 FIB 中的 piece table（Clx）还原正文文本。仅支持 Word 97 及以上格式。
"""

from __future__ import annotations

import struct
from pathlib import Path

MAX_PIECES = 200


def extract_doc_text(path: str | Path, *, max_chars: int = 2000) -> str:
    """抽取 .doc 正文文本。未安装 olefile 时抛 ImportError；解析失败返回空串。"""
    try:
        import olefile
    except ImportError as exc:
        raise ImportError("DOC 抽取需要 olefile：pip install olefile") from exc

    try:
        return _read_doc(olefile, Path(path))[:max_chars]
    except Exception:
        return ""


def _read_doc(olefile, p: Path) -> str:
    ole = olefile.OleFileIO(str(p))
    try:
        wd = ole.openstream("WordDocument").read()
        if len(wd) < 0x01AA:
            return ""
        flags = struct.unpack("<H", wd[0x0A:0x0C])[0]
        table_name = "1Table" if (flags >> 9) & 1 else "0Table"
        if not ole.exists(table_name):
            return ""
        table = ole.openstream(table_name).read()

        fc_clx = struct.unpack("<I", wd[0x01A2:0x01A6])[0]
        lcb_clx = struct.unpack("<I", wd[0x01A6:0x01AA])[0]
        clx = table[fc_clx:fc_clx + lcb_clx]

        pieces: list[str] = []
        i = 0
        while i < len(clx):
            kind = clx[i]
            if kind == 1:  # Prc：跳过
                cb = struct.unpack("<H", clx[i + 1:i + 3])[0]
                i += 3 + cb
            elif kind == 2:  # Pcdt：piece table
                lcb = struct.unpack("<I", clx[i + 1:i + 5])[0]
                pcdt = clx[i + 5:i + 5 + lcb]
                n = max((lcb - 4) // 12, 0)
                cps = [
                    struct.unpack("<I", pcdt[j * 4:j * 4 + 4])[0]
                    for j in range(n + 1)
                ]
                for j in range(min(n, MAX_PIECES)):
                    off = (n + 1) * 4 + j * 8
                    fc = struct.unpack("<I", pcdt[off + 2:off + 6])[0]
                    length = cps[j + 1] - cps[j]
                    if fc & 0x40000000:  # 压缩：单字节 cp1252
                        start = (fc & 0x3FFFFFFF) // 2
                        data = wd[start:start + length]
                        pieces.append(data.decode("cp1252", errors="ignore"))
                    else:  # 未压缩：UTF-16LE
                        start = fc & 0x3FFFFFFF
                        data = wd[start:start + length * 2]
                        pieces.append(data.decode("utf-16-le", errors="ignore"))
                break
            else:
                break
        return "".join(pieces)
    finally:
        ole.close()
