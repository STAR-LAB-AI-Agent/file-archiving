"""命令行入口。

子命令：
    scan      扫描目录，输出结构化文件清单
    plan      扫描 + 管道 → 生成计划/预览（不落盘）
    apply     执行 plan.json（落盘，记录撤销映射）
    organize  一键全流程整理：scan → 管道 → plan →（确认后）apply
    ask       自然语言指令 → 智能体 → 管道 → 计划/执行
    undo      一键撤销最近 N 次整理

用法：
    file_organizer scan     --path demo
    file_organizer plan     --path demo [--pipeline p.json] [--output plan.json]
    file_organizer apply    --plan plan.json [--conflict skip] [--only a001,a002]
    file_organizer organize --path demo --dry-run        # 只预览
    file_organizer organize --path demo --yes            # 确认并执行
    file_organizer ask "按类型整理" --path demo --yes     # 自然语言
    file_organizer undo     --path demo [--n 1]          # 撤销最近一次
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent import AgentError, run_instruction
from .executor import apply_plan
from .pipeline import apply_options, load_pipeline, run_pipeline
from .planner import build_plan, render_preview
from .scanner import scan_directory
from .security import SecurityError, assert_safe_root
from .stages.where import StageError
from .theme import discover_content_rules
from .undo import undo_last
from .watcher import start_watcher


# ---------- scan ----------

def _add_scan_parser(subparsers) -> None:
    p = subparsers.add_parser("scan", help="扫描目录，输出结构化文件清单")
    p.add_argument("--path", required=True, help="要扫描的目录路径")
    p.add_argument("--no-recursive", action="store_true", help="不递归子目录")
    p.add_argument("--include-hidden", action="store_true", help="包含隐藏文件")
    p.add_argument("--follow-symlinks", action="store_true", help="把符号链接文件纳入结果")
    p.add_argument("--max-depth", type=int, default=None, help="递归最大深度")
    p.add_argument("--table", action="store_true", help="以表格形式输出（默认 JSON）")
    p.set_defaults(func=_cmd_scan)


def _cmd_scan(args) -> int:
    try:
        result = scan_directory(
            args.path,
            recursive=not args.no_recursive,
            include_hidden=args.include_hidden,
            follow_symlinks=args.follow_symlinks,
            max_depth=args.max_depth,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    if args.table:
        _print_table(result)
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


# ---------- plan / apply / organize ----------

def _scan_and_plan(path: str, pipeline_source, *, rules=None, preserve: bool = False) -> dict:
    """扫描目录 + 执行管道 + 生成计划（不落盘）。"""
    root = str(Path(path).expanduser().resolve())
    assert_safe_root(root)  # 安全：拒绝操作系统目录
    result = scan_directory(root)
    desc = apply_options(load_pipeline(pipeline_source), rules=rules, preserve=preserve)
    entries = run_pipeline(desc, result.entries, root=root)
    return build_plan(entries, root=root)


def _add_plan_parser(subparsers) -> None:
    p = subparsers.add_parser("plan", help="扫描 + 管道 → 生成计划/预览（不落盘）")
    p.add_argument("--path", required=True, help="要整理的目录路径")
    p.add_argument("--pipeline", default=None, help="pipeline JSON 文件路径（缺省用默认管道）")
    p.add_argument("--rules", default=None, help="内容分类规则文件（JSON/YAML，见 discover-rules）")
    p.add_argument("--preserve-structure", action="store_true", help="就地分类，保留嵌套目录结构（不扁平化）")
    p.add_argument("--output", default=None, help="把 plan.json 保存到该路径")
    p.set_defaults(func=_cmd_plan)


def _cmd_plan(args) -> int:
    try:
        plan = _scan_and_plan(args.path, args.pipeline, rules=args.rules, preserve=args.preserve_structure)
    except (FileNotFoundError, NotADirectoryError, ValueError, StageError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    print(render_preview(plan))
    if args.output:
        Path(args.output).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n已保存计划: {args.output}")
    return 0


def _add_apply_parser(subparsers) -> None:
    p = subparsers.add_parser("apply", help="执行 plan.json（落盘，记录撤销映射）")
    p.add_argument("--plan", required=True, help="plan.json 文件路径")
    p.add_argument("--conflict", default="skip", choices=["skip", "overwrite", "rename_suffix"])
    p.add_argument("--only", default=None, help="只执行这些 action id（逗号分隔）")
    p.add_argument("--exclude", default=None, help="跳过这些 action id（逗号分隔）")
    p.add_argument("--dry-run", action="store_true", help="只模拟，不落盘")
    p.set_defaults(func=_cmd_apply)


def _cmd_apply(args) -> int:
    try:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"错误: 无法读取计划文件: {exc}", file=sys.stderr)
        return 2
    only = set(args.only.split(",")) if args.only else None
    exclude = set(args.exclude.split(",")) if args.exclude else None
    result = apply_plan(
        plan, conflict_policy=args.conflict, dry_run=args.dry_run,
        only=only, exclude=exclude,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _add_organize_parser(subparsers) -> None:
    p = subparsers.add_parser("organize", help="一键全流程整理：scan→管道→plan→（确认后）apply")
    p.add_argument("--path", required=True, help="要整理的目录路径")
    p.add_argument("--pipeline", default=None, help="pipeline JSON 文件路径（缺省用默认管道）")
    p.add_argument("--rules", default=None, help="内容分类规则文件（JSON/YAML，见 discover-rules）")
    p.add_argument("--preserve-structure", action="store_true", help="就地分类，保留嵌套目录结构（不扁平化）")
    p.add_argument("--conflict", default="skip", choices=["skip", "overwrite", "rename_suffix"])
    p.add_argument("--yes", action="store_true", help="确认并执行（否则只预览计划）")
    p.add_argument("--dry-run", action="store_true", help="只生成计划，不执行")
    p.set_defaults(func=_cmd_organize)


def _cmd_organize(args) -> int:
    try:
        plan = _scan_and_plan(args.path, args.pipeline, rules=args.rules, preserve=args.preserve_structure)
    except (FileNotFoundError, NotADirectoryError, ValueError, StageError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    print(render_preview(plan))
    if args.dry_run:
        print("\n[dry-run] 未执行任何改动。")
        return 0
    if not args.yes:
        print("\n未执行。请加 --yes 确认执行，或改用 plan/apply 分步操作。")
        return 0

    result = apply_plan(plan, conflict_policy=args.conflict)
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---------- ask（自然语言入口） ----------

def _add_ask_parser(subparsers) -> None:
    p = subparsers.add_parser("ask", help="自然语言指令 → 智能体 → 管道 → 计划/执行")
    p.add_argument("instruction", help="自然语言指令，如：按类型整理 / 重命名为 {date}_{index:03d}{suffix} / 移到 归档")
    p.add_argument("--path", required=True, help="要整理的目录路径")
    p.add_argument("--rules", default=None, help="内容分类规则文件（JSON/YAML，见 discover-rules）")
    p.add_argument("--preserve-structure", action="store_true", help="就地分类，保留嵌套目录结构（不扁平化）")
    p.add_argument("--conflict", default="skip", choices=["skip", "overwrite", "rename_suffix"])
    p.add_argument("--yes", action="store_true", help="确认并执行（否则只预览）")
    p.add_argument("--dry-run", action="store_true", help="只生成计划，不执行")
    p.set_defaults(func=_cmd_ask)


def _cmd_ask(args) -> int:
    try:
        out = run_instruction(
            args.instruction,
            args.path,
            execute=args.yes and not args.dry_run,
            conflict_policy=args.conflict,
            rules=args.rules,
            preserve=args.preserve_structure,
        )
    except (AgentError, StageError, FileNotFoundError, NotADirectoryError, ValueError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    print(f"指令: {out['instruction']}")
    print(f"意图: {out['intent']['name']}  参数: {out['intent'].get('params', {})}")
    print(f"管道: {' → '.join(s['op'] for s in out['pipeline']['stages'])}")
    print()
    print(out["preview"])
    if out.get("result") is None:
        if args.dry_run:
            print("\n[dry-run] 未执行。")
        else:
            print("\n未执行。加 --yes 确认执行。")
        return 0
    print("\n" + json.dumps(out["result"], ensure_ascii=False, indent=2))
    return 0


# ---------- undo（一键撤销） ----------

def _add_undo_parser(subparsers) -> None:
    p = subparsers.add_parser("undo", help="一键撤销最近 N 次整理")
    p.add_argument("--path", required=True, help="目标目录（定位撤销历史）")
    p.add_argument("--n", type=int, default=1, help="回滚最近 N 次（默认 1）")
    p.set_defaults(func=_cmd_undo)


def _cmd_undo(args) -> int:
    result = undo_last(args.path, n=args.n)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---------- discover-rules（LLM 内容主题发现） ----------

def _add_discover_rules_parser(subparsers) -> None:
    p = subparsers.add_parser("discover-rules", help="用大模型从目录内容归纳分类规则")
    p.add_argument("--path", required=True, help="要分析的目录路径")
    p.add_argument("--output", default=None, help="把规则保存到 JSON 文件")
    p.add_argument("--max-files", type=int, default=15, help="采样文件数上限（默认 15）")
    p.add_argument("--max-chars", type=int, default=400, help="每个文件摘要长度上限（默认 400）")
    p.set_defaults(func=_cmd_discover_rules)


def _cmd_discover_rules(args) -> int:
    try:
        content_rules = discover_content_rules(
            args.path, max_files=args.max_files, max_chars=args.max_chars
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    full = {"content_rules": content_rules}
    print(json.dumps(full, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).write_text(
            json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n已保存规则: {args.output}")
    return 0


# ---------- watch（自动监听） ----------

def _add_watch_parser(subparsers) -> None:
    p = subparsers.add_parser("watch", help="监听目录，新文件自动整理（Ctrl+C 停止）")
    p.add_argument("--path", required=True, help="要监听的目录路径")
    p.add_argument("--pipeline", default=None, help="pipeline JSON 文件路径（缺省用默认管道）")
    p.add_argument("--debounce", type=float, default=2.0, help="防抖秒数（默认 2.0）")
    p.add_argument("--conflict", default="skip", choices=["skip", "overwrite", "rename_suffix"])
    p.add_argument("--dry-run", action="store_true", help="只预览，不落盘")
    p.set_defaults(func=_cmd_watch)


def _watch_on_event(out: dict) -> None:
    s = out["plan"]["summary"]
    if out.get("result") is None:
        print(f"[watch][dry-run] 计划 {s['total']} 个文件（未执行）")
        return
    r = out["result"]["summary"]
    print(f"[watch] applied={r['applied']} skipped={r['skipped']} failed={r['failed']}")


def _cmd_watch(args) -> int:
    def _on_start() -> None:
        print(f"监听目录: {args.path}")
        print("新文件落入顶层将自动整理；按 Ctrl+C 停止。")

    try:
        start_watcher(
            args.path,
            pipeline=args.pipeline,
            debounce=args.debounce,
            conflict_policy=args.conflict,
            dry_run=args.dry_run,
            on_start=_on_start,
            on_event=_watch_on_event,
        )
    except ImportError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    except SecurityError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    print("已停止监听。")
    return 0


# ---------- 其他 ----------

def _print_table(result) -> None:
    print(f"扫描目录: {result.root}")
    print(
        f"文件数: {result.total_files}  目录数: {result.total_dirs}  "
        f"跳过: {len(result.skipped)}"
    )
    print("-" * 110)
    print(f"{'相对路径':<44} {'扩展名':<10} {'大小(字节)':>12}  修改时间")
    print("-" * 110)
    for e in result.entries:
        print(f"{e.relative_path:<44} {e.extension:<10} {e.size:>12}  {e.mtime_iso}")
    for s in result.skipped:
        print(f"[跳过] {s['path']}  ->  {s['reason']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file_organizer",
        description="AI 文件智能整理 —— Script/CLI 层",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")
    _add_scan_parser(subparsers)
    _add_plan_parser(subparsers)
    _add_apply_parser(subparsers)
    _add_organize_parser(subparsers)
    _add_ask_parser(subparsers)
    _add_undo_parser(subparsers)
    _add_watch_parser(subparsers)
    _add_discover_rules_parser(subparsers)
    return parser


def _reconfigure_stdio() -> None:
    """强制 stdout/stderr 使用 UTF-8，避免中文 Windows（GBK）控制台输出乱码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass  # 非文本流或不支持 reconfigure 时忽略


def main(argv: list[str] | None = None) -> int:
    _reconfigure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
