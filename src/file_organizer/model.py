"""统一数据模型：FileRecord。

所有整理原语（stage）围绕同一份 FileRecord 列表工作，
通过 category / tags / new_name / target 等字段在阶段间传递中间结果。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class FileRecord:
    # —— 扫描字段（scanner 写入）——
    path: str  # 绝对路径
    relative_path: str  # 相对根目录，统一 "/" 分隔
    name: str  # 文件名（含扩展名）
    stem: str  # 去掉最后一个扩展名
    suffix: str  # 扩展名（含点，小写），如 ".pdf"
    extension: str  # 扩展名（不含点，小写），如 "pdf"
    mime_type: str
    size: int  # 字节数
    mtime: float  # 修改时间（epoch 秒）
    mtime_iso: str  # 修改时间（ISO 8601，UTC）
    is_symlink: bool = False
    mtime_days: float = 0.0  # 距今多少天（扫描时预计算，供 filter 使用）

    # —— stage 字段（分类/重命名/移动/去重等写入，默认空）——
    category: str | None = None  # classify 写入
    tags: list[str] = field(default_factory=list)  # tag 写入
    dup_group: int | None = None  # dedup 写入
    is_kept: bool = True  # dedup 写入：是否保留（重复项置 False）
    new_name: str | None = None  # rename 写入（完整新文件名，含扩展名）
    target: str | None = None  # move 写入（目标目录绝对路径）
    external_target: bool = False  # move 写入：目标是否显式跨出根目录（to_path 绝对路径）

    def to_dict(self) -> dict:
        return asdict(self)
