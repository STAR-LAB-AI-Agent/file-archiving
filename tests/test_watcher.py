"""watch 自动监听单测。未装 watchdog 时优雅跳过。"""

import os
import time

import pytest

pytest.importorskip("watchdog")

from file_organizer.security import SecurityError
from file_organizer.watcher import (
    DebounceTrigger,
    organize_once,
    should_trigger,
    start_watcher,
)


def test_should_trigger_created_top_level(tmp_path):
    assert should_trigger("created", False, str(tmp_path / "a.pdf"), None, str(tmp_path)) is True


def test_should_trigger_created_subdir(tmp_path):
    assert should_trigger("created", False, str(tmp_path / "sub" / "a.pdf"), None, str(tmp_path)) is False


def test_should_trigger_directory_event(tmp_path):
    assert should_trigger("created", True, str(tmp_path), None, str(tmp_path)) is False


def test_should_trigger_moved_into_root(tmp_path):
    outside = str(tmp_path.parent / "outside.pdf")
    assert should_trigger("moved", False, outside, str(tmp_path / "a.pdf"), str(tmp_path)) is True


def test_should_trigger_moved_out_of_root(tmp_path):
    # organize 把顶层文件移入子目录的事件，不应触发（防回环）
    assert (
        should_trigger("moved", False, str(tmp_path / "a.pdf"), str(tmp_path / "文档" / "a.pdf"), str(tmp_path))
        is False
    )


def test_organize_once_top_level(tmp_path):
    (tmp_path / "报告.pdf").write_text("pdf")
    (tmp_path / "照片.jpg").write_text("jpg")
    (tmp_path / "文档").mkdir()
    (tmp_path / "文档" / "旧.txt").write_text("txt")  # 子目录里的旧文件不应被重复处理

    out = organize_once(
        str(tmp_path),
        {"stages": [{"op": "classify", "by": "type"}, {"op": "move", "rule": "by_category"}]},
    )
    assert out["result"]["summary"]["applied"] == 2
    assert (tmp_path / "文档" / "报告.pdf").exists()
    assert (tmp_path / "图片" / "照片.jpg").exists()
    assert (tmp_path / "文档" / "旧.txt").exists()  # 非递归扫描，旧文件保持原位


def test_start_watcher_rejects_system_dir():
    bad = r"C:\Windows" if os.name == "nt" else "/etc"
    with pytest.raises(SecurityError):
        start_watcher(bad)


def test_debounce_trigger():
    calls: list[int] = []
    t = DebounceTrigger(lambda: calls.append(1), debounce=0.05)
    t.notify()
    t.notify()  # 重置计时，应只回调一次
    assert calls == []
    time.sleep(0.15)
    assert calls == [1]
    t.shutdown()
