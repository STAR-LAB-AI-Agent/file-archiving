"""安全控制：目录白名单、越界检查、系统目录保护、风险分级。"""

from __future__ import annotations

import os
from pathlib import Path


class SecurityError(PermissionError):
    """安全策略拒绝。"""


_SYSTEM_DIRS_WINDOWS = [r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)"]
_SYSTEM_DIRS_POSIX = ["/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/boot", "/proc", "/sys", "/dev"]


def is_within(path: str | Path, root: str | Path) -> bool:
    """判断 path 是否位于 root 目录内（含 root 本身）。"""
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def assert_within(path, root, *, label: str = "路径") -> None:
    """path 不在 root 内时抛 SecurityError。"""
    if not is_within(path, root):
        raise SecurityError(f"{label}超出允许目录范围: {path}（根目录 {root}）")


def is_system_path(path: str | Path) -> bool:
    """判断是否为操作系统受保护目录。"""
    r = str(Path(path).resolve()).lower()
    sep = "\\" if os.name == "nt" else "/"
    dirs = _SYSTEM_DIRS_WINDOWS if os.name == "nt" else _SYSTEM_DIRS_POSIX
    for d in dirs:
        dl = d.lower().rstrip("\\/")
        if r == dl or r.startswith(dl + sep):
            return True
    return False


def assert_safe_root(path) -> None:
    """拒绝把操作系统目录作为整理根目录。"""
    if is_system_path(path):
        raise SecurityError(f"拒绝操作系统目录作为整理目录: {path}")


def risk_of(op: str) -> str:
    """动作风险分级。"""
    if op in ("move", "rename", "move_and_rename"):
        return "medium"
    if op in ("delete", "unlink", "rmtree"):
        return "high"
    return "low"
