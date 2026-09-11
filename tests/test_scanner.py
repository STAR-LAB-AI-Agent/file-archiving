"""scanner 模块单元测试。

覆盖维度：
- 正常输入：空目录 / 嵌套递归 / 元数据（大小·扩展名·MIME·时间）/ 大文件
- 边界情况：非递归 / 隐藏文件过滤与包含 / max_depth
- 异常情况：路径不存在 / 路径非目录 / 无权限目录（POSIX）/ 符号链接
"""

import os

import pytest

from file_organizer.scanner import scan_directory


# ---------- 正常输入 ----------

def test_scan_empty_dir(tmp_path):
    result = scan_directory(tmp_path)
    assert result.total_files == 0
    assert result.total_dirs == 0
    assert result.entries == []
    assert result.skipped == []


def test_scan_nested_recursive(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.pdf").write_text("pdf", encoding="utf-8")
    (sub / "deep").mkdir()
    (sub / "deep" / "c.jpg").write_bytes(b"\xff\xd8\xff")

    result = scan_directory(tmp_path)
    rel = {e.relative_path for e in result.entries}
    assert rel == {"a.txt", "sub/b.pdf", "sub/deep/c.jpg"}
    assert result.total_files == 3
    assert result.total_dirs == 2  # sub 与 sub/deep


def test_scan_metadata(tmp_path):
    f = tmp_path / "报告.PDF"
    f.write_bytes(b"x" * 1024)

    result = scan_directory(tmp_path)
    assert len(result.entries) == 1
    e = result.entries[0]
    assert e.name == "报告.PDF"
    assert e.stem == "报告"
    assert e.suffix == ".pdf"  # 扩展名统一小写
    assert e.extension == "pdf"
    assert e.mime_type == "application/pdf"
    assert e.size == 1024
    assert e.mtime > 0
    assert e.mtime_iso.endswith("+00:00")


def test_scan_large_file(tmp_path):
    f = tmp_path / "big.bin"
    size = 1024 * 1024  # 1 MB
    f.write_bytes(b"\x00" * size)
    result = scan_directory(tmp_path)
    assert len(result.entries) == 1
    assert result.entries[0].size == size


# ---------- 边界情况 ----------

def test_scan_non_recursive(tmp_path):
    (tmp_path / "top.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "inner.txt").write_text("y", encoding="utf-8")

    result = scan_directory(tmp_path, recursive=False)
    assert [e.relative_path for e in result.entries] == ["top.txt"]
    assert result.total_dirs == 1


def test_scan_hidden_skipped_by_default(tmp_path):
    (tmp_path / ".hidden.txt").write_text("h", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("v", encoding="utf-8")
    result = scan_directory(tmp_path)
    assert {e.name for e in result.entries} == {"visible.txt"}


def test_scan_hidden_included(tmp_path):
    (tmp_path / ".hidden.txt").write_text("h", encoding="utf-8")
    result = scan_directory(tmp_path, include_hidden=True)
    assert {e.name for e in result.entries} == {".hidden.txt"}


def test_scan_max_depth(tmp_path):
    (tmp_path / "d1").mkdir()
    (tmp_path / "d1" / "d2").mkdir()
    (tmp_path / "d1" / "d2" / "deep.txt").write_text("x", encoding="utf-8")
    result = scan_directory(tmp_path, max_depth=1)
    assert result.total_files == 0  # 文件位于第 2 层，超出 max_depth=1


def test_scan_negative_max_depth_raises(tmp_path):
    with pytest.raises(ValueError):
        scan_directory(tmp_path, max_depth=-1)


# ---------- 异常情况 ----------

def test_scan_nonexistent_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_directory(tmp_path / "nope")


def test_scan_not_a_directory_raises(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        scan_directory(f)


@pytest.mark.skipif(os.name == "nt", reason="POSIX 权限位在 Windows 上不生效")
def test_scan_permission_denied_skipped(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "secret.txt").write_text("s", encoding="utf-8")
    os.chmod(locked, 0o000)
    try:
        result = scan_directory(tmp_path)
        # 不可读目录记录到 skipped，且其中的文件不出现在 entries 中
        assert any("locked" in s["path"] for s in result.skipped)
        assert all("secret.txt" not in e.relative_path for e in result.entries)
    finally:
        os.chmod(locked, 0o755)


@pytest.mark.skipif(os.name == "nt", reason="创建符号链接在 Windows 上需额外权限")
def test_scan_skips_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("t", encoding="utf-8")
    link = tmp_path / "link.txt"
    os.symlink(target, link)

    result = scan_directory(tmp_path)
    # 默认不跟随符号链接 -> link.txt 被跳过
    assert {e.name for e in result.entries} == {"target.txt"}
