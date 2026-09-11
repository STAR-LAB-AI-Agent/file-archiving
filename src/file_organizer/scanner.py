"""目录扫描模块。

递归遍历目录，产出结构化文件清单与元数据（大小 / 修改时间 / 扩展名 / MIME）。
纯标准库实现（pathlib + mimetypes），可独立运行，供 classifier / planner 等复用。

- 符号链接默认跳过，避免链接环导致无限递归；即便开启 follow_symlinks 也不递归符号链接目录。
- 无法读取的目录/文件不中断扫描，记录到 skipped。
- 扩展名统一小写，便于分类规则做大小写无关匹配。
"""

from __future__ import annotations

import mimetypes
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .model import FileRecord

# 常见扩展名 -> MIME 的确定性映射（Windows 下 mimetypes 依赖注册表，
# 显式内置常用类型可保证行为跨平台一致；后续可用 python-magic 做更精确识别）。
_COMMON_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".mp3": "audio/mpeg",
    ".wav": "audio/x-wav",
    ".mp4": "video/mp4",
    ".zip": "application/zip",
}


@dataclass
class ScanResult:
    """扫描结果：文件清单 + 跳过项 + 汇总。"""

    root: str
    entries: list[FileRecord] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "total_skipped": len(self.skipped),
            "files": [e.to_dict() for e in self.entries],
            "skipped": self.skipped,
        }


def _guess_mime(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in _COMMON_MIME:
        return _COMMON_MIME[suffix]
    return mimetypes.guess_type(name.lower())[0] or "application/octet-stream"


def _build_entry(item: Path, root: Path) -> FileRecord:
    stat = item.stat()
    mtime = stat.st_mtime
    suffix = item.suffix.lower()
    return FileRecord(
        path=str(item),
        relative_path=item.relative_to(root).as_posix(),  # 统一用 "/" 分隔，跨平台一致
        name=item.name,
        stem=item.stem,
        suffix=suffix,
        extension=suffix.lstrip("."),
        mime_type=_guess_mime(item.name),
        size=stat.st_size,
        mtime=mtime,
        mtime_iso=datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
        is_symlink=item.is_symlink(),
        mtime_days=(time.time() - mtime) / 86400.0,
    )


def scan_directory(
    path: str | Path,
    *,
    recursive: bool = True,
    include_hidden: bool = False,
    follow_symlinks: bool = False,
    max_depth: int | None = None,
) -> ScanResult:
    """扫描目录，返回结构化文件清单。

    参数:
        path: 要扫描的目录路径。
        recursive: 是否递归子目录，默认 True。
        include_hidden: 是否包含以 "." 开头的隐藏项，默认 False。
        follow_symlinks: 是否把符号链接文件纳入结果，默认 False（跳过）。
        max_depth: 递归最大深度（None 表示不限；0 表示仅当前层）。

    异常:
        FileNotFoundError: 路径不存在。
        NotADirectoryError: 路径不是目录。
        ValueError: max_depth 为负数。
    """
    if max_depth is not None and max_depth < 0:
        raise ValueError(f"max_depth 不能为负数: {max_depth}")

    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是目录: {root}")

    result = ScanResult(root=str(root))
    _walk(
        root,
        root,
        recursive=recursive,
        include_hidden=include_hidden,
        follow_symlinks=follow_symlinks,
        max_depth=max_depth,
        depth=0,
        result=result,
    )
    result.entries.sort(key=lambda e: e.relative_path)
    result.skipped.sort(key=lambda s: s["path"])
    return result


def _walk(
    current: Path,
    root: Path,
    *,
    recursive: bool,
    include_hidden: bool,
    follow_symlinks: bool,
    max_depth: int | None,
    depth: int,
    result: ScanResult,
) -> None:
    try:
        children = sorted(current.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        result.skipped.append({"path": str(current), "reason": f"无法读取目录: {exc}"})
        return

    for item in children:
        if item.name.startswith(".") and not include_hidden:
            continue

        try:
            is_symlink = item.is_symlink()
        except OSError as exc:
            result.skipped.append({"path": str(item), "reason": f"无法读取: {exc}"})
            continue
        if is_symlink and not follow_symlinks:
            continue

        try:
            if item.is_dir():
                result.total_dirs += 1
                # 符号链接目录不递归，防止链接环导致死循环
                if recursive and not is_symlink and (max_depth is None or depth < max_depth):
                    _walk(
                        item,
                        root,
                        recursive=recursive,
                        include_hidden=include_hidden,
                        follow_symlinks=follow_symlinks,
                        max_depth=max_depth,
                        depth=depth + 1,
                        result=result,
                    )
                continue
            if item.is_file():
                result.total_files += 1
                result.entries.append(_build_entry(item, root))
        except OSError as exc:
            result.skipped.append({"path": str(item), "reason": f"无法读取: {exc}"})
