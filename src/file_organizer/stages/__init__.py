"""整理原语（stage）包。

每个 stage 都是纯函数：stage(entries, params, ctx) -> entries，不落盘，
通过 STAGE_REGISTRY 注册后由 pipeline 按需组合。

统一接口约定：
    entries : list[FileRecord]   —— 流动的“行记录”列表
    params  : dict               —— 该 stage 的专属参数（来自 pipeline 描述）
    ctx     : dict               —— 共享上下文（root、rules 等）
"""

from __future__ import annotations

from .classify import classify_stage
from .dedup import dedup_stage
from .filter import filter_stage
from .move import move_stage
from .rename import rename_stage
from .sort import sort_stage
from .tag import tag_stage

# 可组合原语注册表（新增 stage 时在此登记即可，不改动已有原语）
STAGE_REGISTRY = {
    "filter": filter_stage,
    "classify": classify_stage,
    "sort": sort_stage,
    "rename": rename_stage,
    "move": move_stage,
    "tag": tag_stage,
    "dedup": dedup_stage,
    # 预留: archive
}
