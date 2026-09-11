"""监听触发式智能体整理：递归监听目录变动 → 通知大模型 → 执行其整理方案。

与 CLI 的 `watch` 子命令的区别：
- `watch`：只监听顶层、用固定管道、不调用大模型；
- 本模块（watch-agent）：递归监听所有子目录，任何变动后调用大模型（默认 DeepSeek，
  OpenAI 兼容接口）生成整理方案（pipeline），再执行该方案。

防回环：整理期间置 busy 标志并冷却一段时间，忽略整理自身产生的文件移动事件。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

from .executor import apply_plan
from .llm import chat
from .pipeline import run_pipeline
from .planner import build_plan
from .scanner import scan_directory
from .security import assert_safe_root

log = logging.getLogger(__name__)

# 大模型不可用时的回退方案：按类型就地分类（保留目录结构，不扁平化）
DEFAULT_PIPELINE: dict = {
    "stages": [
        {"op": "classify", "by": "type"},
        {"op": "move", "rule": "by_category", "preserve": True},
    ]
}

SYSTEM_PROMPT = """你是文件整理智能体。用户监听的目录发生了变动，请决定如何整理。

你必须只输出一个 pipeline（JSON），结构：
{"stages": [{"op": "...", ...}, ...]}

可用整理原语（stage）：
- classify : 分类，参数 by ∈ {type, name, content}，可选 mode ∈ {overwrite, append}
- filter   : 筛选，参数 where
- sort     : 排序，参数 by(name|size|mtime|type|category) + order(asc|desc)
- rename   : 重命名，参数 template + 可选 where
- move     : 移动，参数 rule(by_category|to_path)，可选 target / preserve
- dedup    : 内容去重

where 条件语法：{"field","op","value"} | {"and":[...]} | {"or":[...]} | {"not":...}
field ∈ name/stem/suffix/extension/mime_type/size/mtime/category/tags
op ∈ eq/ne/in/not_in/gt/gte/lt/lte/contains/startswith/endswith/regex

要求：
1. 只输出一个 JSON 对象，不要解释，不要 markdown 代码块。
2. 整理必须【保留目录结构】：move 使用 preserve=true（就地分类），不要扁平化。
3. 分类名用中文（文档/图片/表格/演示/压缩包/音频/视频/程序/其他）。
4. 不确定时使用默认方案：
{"stages":[{"op":"classify","by":"type"},{"op":"move","rule":"by_category","preserve":true}]}
"""


class ChangeCollector:
    """线程安全地收集变动文件路径，并记录最后一次变动时间（供防抖判断）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._paths: set[str] = set()
        self._last = 0.0

    def add(self, path: str) -> None:
        with self._lock:
            self._paths.add(path)
            self._last = time.time()

    def pending(self) -> tuple[list[str], float]:
        """返回 (去重排序后的变动路径, 最后一次变动时间)。"""
        with self._lock:
            return sorted(self._paths), self._last

    def drain(self) -> list[str]:
        """取出并清空已收集的路径。"""
        with self._lock:
            paths = sorted(self._paths)
            self._paths.clear()
            self._last = 0.0
            return paths

    def clear(self) -> None:
        with self._lock:
            self._paths.clear()
            self._last = 0.0

    def __len__(self) -> int:
        with self._lock:
            return len(self._paths)


def parse_pipeline_json(text: str) -> dict:
    """从大模型返回文本中解析 pipeline JSON（容忍 markdown 代码块）。"""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        t = t.strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    obj = json.loads(t)
    if not isinstance(obj, dict):
        raise ValueError(f"期望 JSON 对象，得到 {type(obj).__name__}")
    return obj


def build_change_prompt(root: str, changed: list[str]) -> str:
    """构造告知大模型「目录有变动」的用户提示。"""
    root_path = Path(root)
    uniq = sorted(set(changed))
    lines = [f"监听目录：{root}", "", "本次变动（新增 / 修改 / 移入的文件）："]
    for p in uniq[:50]:
        try:
            rel = Path(p).relative_to(root_path).as_posix()
        except ValueError:
            rel = str(p)
        lines.append(f"- {rel}")
    if len(uniq) > 50:
        lines.append(f"... 其余 {len(uniq) - 50} 个省略")
    lines.extend(["", "请给出整理方案（pipeline JSON）。"])
    return "\n".join(lines)


def ask_pipeline(root: str, changed: list[str], *, llm=None) -> dict:
    """把目录变动告知大模型，得到整理方案（pipeline desc）。

    llm 可为 callable(system, user) -> str，便于测试注入；缺省用 llm.chat（DeepSeek）。
    """
    if llm is None:

        def _chat(system: str, user: str) -> str:
            return chat(system, user)

        llm = _chat
    raw = llm(SYSTEM_PROMPT, build_change_prompt(root, changed))
    desc = parse_pipeline_json(raw)
    stages = desc.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError(f"大模型返回的 pipeline 非法：{desc!r}")
    return desc


def organize_once(
    root: str,
    desc: dict,
    *,
    conflict_policy: str = "skip",
    dry_run: bool = False,
) -> dict:
    """用给定 pipeline 整理目录（递归扫描）。返回 {"plan", "result"}。"""
    res = scan_directory(root)
    entries = run_pipeline(desc, res.entries, root=root)
    plan = build_plan(entries, root=root)
    result = None if dry_run else apply_plan(plan, conflict_policy=conflict_policy)
    return {"plan": plan, "result": result}


def watch_and_organize(
    path: str,
    *,
    debounce: float = 5.0,
    cooldown: float = 2.0,
    conflict_policy: str = "skip",
    dry_run: bool = False,
    llm=None,
    on_start=None,
    on_change=None,
    on_plan=None,
    on_result=None,
    on_error=None,
) -> None:
    """递归监听目录，变动后调用大模型生成方案并执行（阻塞，Ctrl+C 停止）。

    - debounce：变动静默多少秒后触发一次（合并批量落盘，避免频繁调用 API）。
    - cooldown：整理后冷却秒数，吞掉整理自身产生的移动事件（防回环）。
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        raise ImportError("watch-agent 需要 watchdog：pip install -e '.[watch]'") from exc

    root = str(Path(path).expanduser().resolve())
    assert_safe_root(root)  # 安全：拒绝操作系统目录

    collector = ChangeCollector()
    busy = threading.Event()

    class _Handler(FileSystemEventHandler):
        def _collect(self, p: str) -> None:
            if not busy.is_set():  # 整理自身产生的事件忽略
                collector.add(p)

        def on_created(self, event):
            if not event.is_directory:
                self._collect(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._collect(event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                self._collect(event.dest_path)

    handler = _Handler()
    observer = Observer()
    observer.schedule(handler, root, recursive=True)  # 递归：含所有末端子目录
    observer.start()
    if on_start is not None:
        on_start(root)

    try:
        while True:
            time.sleep(0.5)
            if busy.is_set():
                continue
            paths, last = collector.pending()
            if not paths or (time.time() - last) < debounce:
                continue  # 仍在变动中，等静默
            changed = collector.drain()
            busy.set()
            try:
                if on_change is not None:
                    on_change(changed)
                try:
                    desc = ask_pipeline(root, changed, llm=llm)
                except Exception as exc:  # 调用大模型失败 → 回退默认方案
                    log.warning("调用大模型失败，回退默认方案：%s", exc)
                    desc = DEFAULT_PIPELINE
                if on_plan is not None:
                    on_plan(desc, changed)
                out = organize_once(root, desc, conflict_policy=conflict_policy, dry_run=dry_run)
                if on_result is not None:
                    on_result(out)
            except Exception as exc:
                log.exception("整理失败")
                if on_error is not None:
                    on_error(exc)
            finally:
                time.sleep(cooldown)  # 冷却：吞掉整理自身产生的移动事件
                collector.clear()
                busy.clear()
    except KeyboardInterrupt:
        log.info("watch-agent 停止 root=%s", root)
    finally:
        observer.stop()
        observer.join()


def _reconfigure_stdio() -> None:
    """强制 UTF-8 + 行缓冲，保证长驻程序输出实时刷新（管道/日志重定向时也生效）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", line_buffering=True)
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    """独立子程序入口：python -m file_organizer.agent_watcher / watch-agent。"""
    _reconfigure_stdio()
    ap = argparse.ArgumentParser(
        prog="watch-agent",
        description="监听触发式智能体文件整理：递归监听目录，变动后通知大模型生成方案并执行",
    )
    ap.add_argument("--path", required=True, help="要监听的目录（递归，含所有子目录）")
    ap.add_argument("--debounce", type=float, default=5.0, help="变动静默多少秒后触发（默认 5）")
    ap.add_argument("--cooldown", type=float, default=2.0, help="整理后冷却秒数（防回环，默认 2）")
    ap.add_argument("--conflict", default="skip", choices=["skip", "overwrite", "rename_suffix"])
    ap.add_argument("--dry-run", action="store_true", help="只让大模型给方案并预览，不落盘")
    ap.add_argument("--model", default=None, help="覆盖 MODEL_NAME（默认读 .env / 环境变量）")
    args = ap.parse_args(argv)

    if args.model:
        os.environ["MODEL_NAME"] = args.model

    def on_start(root: str) -> None:
        print(f"监听目录（递归）：{root}")
        print(f"静默 {args.debounce}s 后触发大模型；按 Ctrl+C 停止。\n")

    def on_change(paths) -> None:
        print(f"[变动] 检测到 {len(paths)} 个文件发生变化")

    def on_plan(desc, changed) -> None:
        ops = " → ".join(s.get("op", "?") for s in desc.get("stages", []))
        print(f"[大模型] 整理方案：{ops}")

    def on_result(out) -> None:
        if out.get("result") is None:
            print(f"[dry-run] 计划 {out['plan']['summary']['total']} 项，未执行")
        else:
            s = out["result"]["summary"]
            print(f"[执行] applied={s['applied']} skipped={s['skipped']} failed={s['failed']}")

    def on_error(exc) -> None:
        print(f"[错误] {exc}", file=sys.stderr)

    watch_and_organize(
        args.path,
        debounce=args.debounce,
        cooldown=args.cooldown,
        conflict_policy=args.conflict,
        dry_run=args.dry_run,
        on_start=on_start,
        on_change=on_change,
        on_plan=on_plan,
        on_result=on_result,
        on_error=on_error,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
