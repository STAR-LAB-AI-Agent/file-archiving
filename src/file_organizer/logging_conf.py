"""结构化日志 + 敏感信息打码。"""

from __future__ import annotations

import logging
import re

# 敏感信息模式：api_key=xxx / token:xxx / password=xxx 等 → 打码
_SENSITIVE = [
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*[:=]\s*\S+"), r"\1=***"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?\S+"), r"\1***"),
]


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """初始化 file_organizer 命名空间的日志（含敏感信息过滤器）。"""
    logger = logging.getLogger("file_organizer")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.addFilter(SensitiveFilter())
    logger.propagate = False
    return logger


def mask_sensitive(text: str) -> str:
    """把文本中的敏感信息打码。"""
    for pat, repl in _SENSITIVE:
        text = pat.sub(repl, text)
    return text


class SensitiveFilter(logging.Filter):
    """日志过滤器：输出前对消息做敏感信息打码。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_sensitive(record.getMessage())
        record.args = ()
        return True
