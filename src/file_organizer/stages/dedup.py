"""dedup 原语：按内容哈希 / 名称 / 大小分组去重（写入 dup_group / is_kept，不落盘）。"""

from __future__ import annotations

import hashlib

from ..model import FileRecord


def dedup_stage(entries: list[FileRecord], params: dict, ctx: dict) -> list[FileRecord]:
    """去重分组。params.by ∈ {content_hash, name, size}；params.keep ∈ {first, oldest, newest}。

    对每组重复文件：写入相同的 dup_group 编号；保留 keep 指定的一个（is_kept=True），
    其余 is_kept=False。后续可用 filter(is_kept==false) + move 把重复项移走。
    """
    by = params.get("by", "content_hash")
    keep = params.get("keep", "first")

    groups: dict[tuple, list[FileRecord]] = {}
    for e in entries:
        groups.setdefault(_dedup_key(e, by), []).append(e)

    gid = 0
    for items in groups.values():
        if len(items) < 2:
            for e in items:
                e.dup_group = None
                e.is_kept = True
            continue
        gid += 1
        kept = _pick_kept(items, keep)
        for e in items:
            e.dup_group = gid
            e.is_kept = e is kept
    return entries


def _dedup_key(e: FileRecord, by: str) -> tuple:
    if by == "name":
        return ("name", e.name)
    if by == "size":
        return ("size", e.size)
    digest = _content_hash(e.path)
    if digest is None:
        return ("unreadable", e.path)  # 不可读文件视为唯一
    return ("hash", digest)


def _pick_kept(items: list[FileRecord], keep: str) -> FileRecord:
    if keep == "oldest":
        return min(items, key=lambda e: e.mtime)
    if keep == "newest":
        return max(items, key=lambda e: e.mtime)
    return items[0]  # first


def _content_hash(path: str) -> str | None:
    """按块计算文件 MD5；文件不可读时返回 None。"""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()
