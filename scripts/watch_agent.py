#!/usr/bin/env python
"""监听触发式智能体文件整理（独立子程序）。

递归监听一个目录，任何变动（含所有末端子目录）在静默 debounce 秒后，
通知大模型（默认 DeepSeek，OpenAI 兼容接口）生成整理方案，并由本脚本执行。

用法：
    # 1) 配置 API Key（或在项目根目录 .env 中填写，见 .env.example）
    set MODEL_API_KEY=sk-xxx            # Windows cmd
    $env:MODEL_API_KEY="sk-xxx"         # Windows PowerShell
    export MODEL_API_KEY=sk-xxx         # Linux / macOS

    # 2) 运行
    python scripts/watch_agent.py --path <目录>
    python scripts/watch_agent.py --path <目录> --debounce 5 --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许在未安装为包时直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from file_organizer.agent_watcher import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
