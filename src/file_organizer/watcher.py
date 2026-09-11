"""watcher：watchdog 目录监听，新文件落入监听目录自动触发默认管道整理。

安全与防回环设计：
- 仅监听顶层（recursive=False），只处理「顶层新文件」；
- should_trigger 过滤掉 organize 自身把文件从顶层移入子目录的事件；
- organize_once 用非递归扫描，避免重扫已整理子目录、避免双重嵌套；
- DebounceTrigger 防抖，批量落盘合并为一次整理。
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from .executor import apply_plan
from .pipeline import load_pipeline, run_pipeline
from .planner import build_plan
from .scanner import scan_directory
from .security import assert_safe_root

log = logging.getLogger(__name__)


def should_trigger(
    event_type: str,
    is_directory: bool,
    src_path: str | None,
    dest_path: str | None,
    root: str,
) -> bool:
    """判断一个文件系统事件是否应触发整理（纯函数，便于单测）。

    只关注「顶层新文件」：
    - created：src 的父目录 == root；
    - moved：dest 的父目录 == root 且 src 的父目录 != root（排除移出顶层的事件）。
    """
    if is_directory:
        return False
    root_path = Path(root)
    if event_type == "created":
        return src_path is not None and Path(src_path).parent == root_path
    if event_type == "moved":
        if dest_path is None:
            return False
        return Path(dest_path).parent == root_path and (
            src_path is None or Path(src_path).parent != root_path
        )
    return False


class DebounceTrigger:
    """防抖触发器：事件到来后延迟 debounce 秒才回调，期间新事件重置计时。"""

    def __init__(self, callback, debounce: float = 2.0):
        self.callback = callback
        self.debounce = debounce
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._running = False

    def notify(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
            if self._running:
                return  # 上一次整理尚未结束，跳过本次（已到达的文件会被那次处理）
            self._running = True
        try:
            self.callback()
        finally:
            with self._lock:
                self._running = False

    def shutdown(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


def organize_once(
    root: str,
    pipeline,
    *,
    conflict_policy: str = "skip",
    dry_run: bool = False,
) -> dict:
    """触发一次整理：非递归扫描顶层 → 管道 → 计划 →（可选）落盘。返回 {"plan", "result"}。"""
    res = scan_directory(root, recursive=False)
    entries = run_pipeline(pipeline, res.entries, root=str(root))
    plan = build_plan(entries, root=str(root))
    result = None if dry_run else apply_plan(plan, conflict_policy=conflict_policy)
    return {"plan": plan, "result": result}


def start_watcher(
    path: str,
    *,
    pipeline=None,
    debounce: float = 2.0,
    conflict_policy: str = "skip",
    dry_run: bool = False,
    on_start=None,
    on_event=None,
) -> None:
    """监听目录，新文件落入顶层时自动整理（阻塞，Ctrl+C 停止）。

    on_start()：观察器成功启动后回调（供 CLI 打印启动提示）。
    on_event(out)：每次触发后回调，参数为 organize_once 的返回值，供 CLI 打印摘要。
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        raise ImportError("watch 需要 watchdog：pip install -e '.[watch]'") from exc

    root = str(Path(path).expanduser().resolve())
    assert_safe_root(root)  # 安全：拒绝操作系统目录
    desc = load_pipeline(pipeline)

    def _organize() -> None:
        log.info("watch 触发整理 root=%s dry_run=%s", root, dry_run)
        out = organize_once(root, desc, conflict_policy=conflict_policy, dry_run=dry_run)
        if on_event is not None:
            on_event(out)

    class _Handler(FileSystemEventHandler):
        def __init__(self):
            self._trigger = DebounceTrigger(_organize, debounce)

        def on_created(self, event):
            if should_trigger("created", event.is_directory, event.src_path, None, root):
                self._trigger.notify()

        def on_moved(self, event):
            if should_trigger("moved", event.is_directory, event.src_path, event.dest_path, root):
                self._trigger.notify()

        def shutdown(self):
            self._trigger.shutdown()

    handler = _Handler()
    observer = Observer()
    observer.schedule(handler, root, recursive=False)
    observer.start()
    if on_start is not None:
        on_start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("watch 停止 root=%s", root)
    finally:
        handler.shutdown()
        observer.stop()
        observer.join()
