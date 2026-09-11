"""LLM 客户端：OpenAI 兼容接口（仅标准库 urllib，无第三方依赖）。

配置通过环境变量（或项目根目录 .env 文件，见 .env.example）：
    MODEL_BASE_URL   默认 https://api.deepseek.com
    MODEL_API_KEY    必填
    MODEL_NAME       默认 deepseek-chat
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _load_dotenv(path: str = ".env") -> None:
    """极简 .env 加载（不覆盖已存在的环境变量）。"""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_config() -> dict:
    """读取 LLM 配置（优先环境变量，其次 .env）。"""
    _load_dotenv()
    return {
        "base_url": os.environ.get("MODEL_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "api_key": os.environ.get("MODEL_API_KEY", ""),
        "model": os.environ.get("MODEL_NAME", DEFAULT_MODEL),
    }


def chat(
    system: str,
    user: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0,
) -> str:
    """调用 OpenAI 兼容 chat/completions，返回 assistant 文本内容。"""
    cfg = get_config()
    base_url = (base_url or cfg["base_url"]).rstrip("/")
    api_key = api_key or cfg["api_key"]
    model = model or cfg["model"]
    if not api_key:
        raise RuntimeError("缺少 MODEL_API_KEY：请设置环境变量或在 .env 中配置")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]
