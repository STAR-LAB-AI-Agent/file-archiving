# ai-file-organizer

一个本地文件整理命令行工具与 agent skill：对目录中的文件进行**扫描、分类、重命名、移动、去重与自动监听**，并在任何改动前给出**计划预览**、支持**一键撤销**。

核心能力全部下沉到可独立运行的 `file_organizer` 命令行工具，不依赖大模型即可使用；分类、重命名、移动等能力被建模为一组**可组合的整理原语（stage）**，由声明式 **pipeline** 按需串联。

## 功能特性

- **目录扫描**：递归遍历，输出文件清单与元数据（大小 / 修改时间 / 扩展名 / MIME）。
- **分类**：按扩展名类型、文件名关键词、或文件内容关键词分类。
- **批量重命名**：按模板（日期 / 序号 / 字段）重命名。
- **定向移动 / 归档**：按条件筛选后移动到指定目录。
- **去重**：按内容哈希找出重复文件。
- **自动监听**：监听目录，新文件落入时自动整理（基于 `watchdog`）。
- **计划预览**：任何写操作前先产出计划，确认后才落盘。
- **一键撤销**：按 history 栈回滚最近 N 次整理。
- **大模型自适应分类**：`discover-rules` 让大模型从目录内容自动归纳分类规则。

## 安装

要求 Python 3.10+。

```bash
pip install -e ".[dev]"                 # 核心 + 测试依赖（核心零第三方依赖）
pip install -e ".[content,watch,config]"  # 可选：PDF/DOCX 内容抽取、目录监听、YAML 规则加载
```

## 快速开始

```bash
# 扫描目录，查看文件清单
file_organizer scan --path demo --table

# 一键整理：先预览计划，确认后执行
file_organizer organize --path demo --dry-run
file_organizer organize --path demo --yes

# 自然语言入口
file_organizer ask "按类型整理" --path demo --yes

# 撤销最近一次整理
file_organizer undo --path demo
```

## 命令行参考

| 子命令 | 说明 |
|---|---|
| `scan` | 扫描目录，输出结构化文件清单 |
| `plan` | 扫描 + 管道 → 生成计划/预览（不落盘） |
| `apply` | 执行 `plan.json`（落盘，记录撤销映射） |
| `organize` | 一键全流程：scan → pipeline → plan →（确认后）apply |
| `ask` | 自然语言指令 → 意图识别 → 管道 → 计划/执行 |
| `undo` | 一键撤销最近 N 次整理 |
| `watch` | 监听目录，新文件自动整理 |
| `discover-rules` | 用大模型从目录内容归纳分类规则 |

常用示例：

```bash
# plan：生成计划，可保存 plan.json 供 apply 使用
file_organizer plan --path demo --pipeline examples/pipeline_rename_example.json
file_organizer plan --path demo --output plan.json

# apply：执行计划，支持冲突策略与选择性执行
file_organizer apply --plan plan.json --conflict skip
file_organizer apply --plan plan.json --only a001,a002

# organize：默认管道 = 按类型分类 → 移动到分类子目录
file_organizer organize --path demo --dry-run
file_organizer organize --path demo --yes

# ask：自然语言入口
file_organizer ask "重命名为 {date}_{index:03d}{suffix}" --path demo --yes
file_organizer ask "移到 归档" --path demo --yes
file_organizer ask "按内容分类" --path demo --yes
file_organizer ask "找出重复文件" --path demo --yes

# undo：撤销最近 N 次
file_organizer undo --path demo
file_organizer undo --path demo --n 2

# watch：监听目录，新文件自动整理（Ctrl+C 停止）
file_organizer watch --path demo
file_organizer watch --path demo --dry-run

# discover-rules：让大模型从内容归纳分类规则，再按规则就地分类（保留嵌套结构）
file_organizer discover-rules --path demo --output rules.json
file_organizer ask "按内容分类" --path demo --rules rules.json --preserve-structure --yes
```

## Pipeline 与整理原语

整理能力由声明式 pipeline 描述，各 stage 顺序执行、可任意组合。pipeline 结构：

```json
{
  "stages": [
    {"op": "classify", "by": "type"},
    {"op": "move", "rule": "by_category"}
  ]
}
```

### Stage 清单

| stage | 作用 | 关键参数 |
|---|---|---|
| `filter` | 按条件筛选（保留满足条件的子集） | `where` |
| `classify` | 分类（写入 `category`） | `by` ∈ {type, name, content}，`mode` ∈ {overwrite, append} |
| `sort` | 排序（影响后续 rename 序号） | `by` ∈ {name, size, mtime, type, category}，`order` ∈ {asc, desc} |
| `rename` | 批量重命名 | `template`，`where`，`index_start` |
| `move` | 计算目标目录 | `rule` ∈ {by_category, to_path}，`target`，`preserve` |
| `tag` | 打标签 | `tags`，`where` |
| `dedup` | 内容哈希去重 | `by`=content_hash，`keep` |

### 条件表达式（where）

```text
where := {"field","op","value"} | {"and":[where...]} | {"or":[where...]} | {"not": where}
field ∈ {name, stem, suffix, extension, mime_type, size, mtime, mtime_days, category, tags}
op    ∈ {eq, ne, in, not_in, gt, gte, lt, lte, contains, startswith, endswith, regex}
```

示例——「扩展名是 pdf 或 docx 且大于 10MB」：

```json
{"and": [
  {"or": [
    {"field": "extension", "op": "eq", "value": "pdf"},
    {"field": "extension", "op": "eq", "value": "docx"}
  ]},
  {"field": "size", "op": "gt", "value": 10485760}
]}
```

### 重命名模板占位符

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{date}` | 修改日期 | `2026-09-08` |
| `{time}` | 修改时间 | `124059` |
| `{stem}` | 原文件名（去扩展名） | `报告` |
| `{name}` | 原文件名（含扩展名） | `报告.pdf` |
| `{suffix}` | 扩展名（含点） | `.pdf` |
| `{ext}` | 扩展名（不含点） | `pdf` |
| `{category}` | 分类名 | `文档` |
| `{index}` | 序号，可格式化 `{index:03d}` | `001` |

### 复合示例

```json
{
  "stages": [
    {"op": "classify", "by": "type"},
    {"op": "sort", "by": "mtime", "order": "asc"},
    {"op": "rename", "template": "{date}_{index:03d}{suffix}", "where": {"field": "category", "op": "endswith", "value": "图片"}},
    {"op": "move", "rule": "by_category"}
  ]
}
```

> 注意「组合即语义」：`sort` 在 `rename` 之前，序号才按时间递增；`classify` 的 `mode=append` 可形成层级分类（如 `内容类/格式类`）。

## 内容分类规则

`classify(by=content)` 抽取文件文本（默认前 512 字符）后按关键词匹配。规则可配置：

- **默认规则**：见 `src/file_organizer/rules.py`。
- **规则文件**：`--rules rules.yaml`（YAML，需 pyyaml）或 `--rules rules.json`（JSON）。
- **自适应规则**：`discover-rules` 采样目录内容，让大模型自动归纳「主题 → 关键词」，适配任意目录。

## 作为 Agent Skill 使用

本项目的 `skills/` 目录定义了一组可供智能体调用的能力说明（`SKILL.md` 及子 Skill），
每条 Skill 最终映射到 `file_organizer` 的某个子命令。调用链：

```text
自然语言 → 意图识别/参数抽取 → Skill → file_organizer CLI → 结果
```

- 预览优先：写 / 移动 / 重命名前先 `plan` 回显，确认后才 `apply`。
- 结构化返回：结果统一为 JSON，便于程序消费。
- 详见 `skills/SKILL.md`。

## 安全与撤销

- **计划预览**：任何改动前先产出计划，默认不落盘。
- **目录保护**：拒绝把操作系统目录作为整理根目录；目标默认必须在根目录内（`move to_path` 使用绝对路径时允许显式跨目录）。
- **冲突处理**：同名目标默认 `skip`，可选 `overwrite` / `rename_suffix`。
- **一键撤销**：每次 apply 写入 `undo_history.json`，`undo` 逆向恢复并清理空目录。

## 开发与测试

```bash
pytest            # 运行全部测试
pytest -v         # 详细输出
```

## 依赖与许可证

| 库 | 许可证 | 用途 |
|---|---|---|
| pathlib / mimetypes / argparse | PSF-2.0（标准库） | 核心文件操作，无需安装 |
| watchdog | Apache-2.0 | 目录监听（`watch` 命令） |
| pypdf | BSD-3-Clause | PDF 内容抽取（可选） |
| python-docx | MIT | DOCX 内容抽取（可选） |
| pyyaml | MIT | YAML 规则加载（可选） |

## License

[MIT](LICENSE) © 2026 赵旭东 · [@violet-041125](https://github.com/violet-041125)
