"""内置整理规则（与 config/rules.yaml 对应）。

config/rules.yaml 为人类可读的规则文档；本模块提供代码内默认值，
并支持通过 load_rules 从 JSON / YAML 文件覆盖默认规则。
"""

from __future__ import annotations

import json
from pathlib import Path

# 扩展名（不含点、小写）-> 分类目录名
DEFAULT_TYPE_RULES: dict[str, list[str]] = {
    "文档": ["pdf", "doc", "docx", "txt", "md"],
    "表格": ["xls", "xlsx", "csv"],
    "演示": ["ppt", "pptx"],
    "图片": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
    "压缩包": ["zip", "rar", "7z", "tar", "gz"],
    "音频": ["mp3", "wav", "flac"],
    "视频": ["mp4", "mkv", "mov"],
    "程序": ["py", "js", "ts", "exe", "msi"],
}

# 文件名关键词（子串匹配）-> 分类目录名
DEFAULT_NAME_RULES: dict[str, list[str]] = {
    "合同": ["合同", "协议", "contract"],
    "发票": ["发票", "报销", "invoice"],
    "简历": ["简历", "resume", "cv"],
}

# 内容关键词（子串匹配，大小写不敏感）-> 分类目录名
# 【不设内置默认】内容分类的关键词必须由调用方（通常是模型）根据目录实际内容提取后提供：
#   - pipeline 里的 rules.content_rules，或
#   - CLI 的 --rules rules.json
# 未提供时 classify(by=content) 会直接报错，避免用写死的规则瞎猜、产生错误分类。
DEFAULT_CONTENT_RULES: dict[str, list[str]] = {}

# 未命中任何规则时的兜底目录
DEFAULT_FOLDER = "其他"


def load_rules(source=None) -> dict:
    """加载整理规则（可配置，替代写死）。

    source 可为：
    - None：返回内置默认规则；
    - dict：作为覆盖项（缺失键用默认）；
    - str/Path：JSON（.json）或 YAML（.yaml/.yml，需 pyyaml）规则文件。

    返回 {"type_rules", "name_rules", "content_rules", "default_folder"}，
    可直接作为 pipeline 的 rules 字段（classify 阶段读取）。
    """
    loaded: dict = {}
    if source is None:
        loaded = {}
    elif isinstance(source, dict):
        loaded = source
    elif isinstance(source, (str, Path)):
        p = Path(source)
        # utf-8-sig：兼容 Windows 编辑器保存出的带 BOM 的规则文件
        text = p.read_text(encoding="utf-8-sig")
        suffix = p.suffix.lower()
        if suffix == ".json":
            loaded = json.loads(text) or {}
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as exc:
                raise ImportError("加载 YAML 规则需要 pyyaml：pip install pyyaml") from exc
            loaded = yaml.safe_load(text) or {}
        else:
            raise ValueError(f"不支持的规则文件格式: {p.suffix}")
    else:
        raise TypeError(f"不支持的规则来源: {type(source)}")

    return {
        "type_rules": loaded.get("type_rules", DEFAULT_TYPE_RULES),
        "name_rules": loaded.get("name_rules", DEFAULT_NAME_RULES),
        "content_rules": loaded.get("content_rules", DEFAULT_CONTENT_RULES),
        "default_folder": loaded.get("default_folder", DEFAULT_FOLDER),
    }
