# ai-file-organizer

一个**本地文件智能整理**命令行工具与 Agent Skill：对目录中的文件进行扫描、分类、批量重命名、移动归档、去重与自动监听；任何改动前先给出**计划预览**，改错了可以**一键撤销**。

核心能力全部下沉到可独立运行的 `file_organizer` 命令行工具（**不依赖大模型即可完成绝大多数整理任务**）；分类、排序、重命名、移动等能力被建模为一组**可组合的整理原语（stage）**，由声明式 **pipeline** 按需串联，因此「组合即语义」——换一种组合方式就得到一种新的整理效果。

---

## 目录

- [项目简介](#项目简介)
- [用户场景](#用户场景)
- [功能特性](#功能特性)
- [仓库结构](#仓库结构)
- [安装](#安装)
- [大模型配置（可选）](#大模型配置可选)
- [快速开始](#快速开始)
- [命令行参考](#命令行参考)（8 个子命令的完整参数）
- [Pipeline 与整理原语](#pipeline-与整理原语)
- [内容分类规则](#内容分类规则)
- [作为 Agent Skill 使用](#作为-agent-skill-使用)
- [作为 nanobot Skill 使用](#作为-nanobot-skill-使用)
- [监听与自动化](#监听与自动化)
- [安全与撤销](#安全与撤销)
- [测试数据（demo/）](#测试数据demo)
- [测试方法](#测试方法)
- [已知问题与限制](#已知问题与限制)
- [开源依赖与许可证](#开源依赖与许可证)
- [License](#license)

---

## 项目简介

本项目解决一个很具体的问题：**目录被文件堆满之后，手动分类、改名、归档既慢又容易出错，而全自动脚本又不敢用（怕它乱动、怕不可回滚）。**

设计上做了三件事：

1. **能力分层，业务逻辑下沉到 CLI。** 大模型只负责「理解意图」和「生成方案」这类模糊环节，真正的扫描/分类/改名/移动全部由确定性代码完成，可独立测试、可离线运行。

   ```text
   意图层      自然语言 / 大模型        ← 可选，负责理解与生成 pipeline
   ↓
   编排层      file_organizer CLI      ← 确定性的命令入口
   ↓
   原语层      pipeline stages         ← filter/classify/sort/rename/move/tag/dedup
   ↓
   基础层      pathlib / watchdog      ← 标准库与通用开源库
   ```

2. **预览优先，写操作永远分两步。** 任何改动先生成**计划（plan）**并回显，确认后才落盘执行。

3. **一键撤销。** 每次执行都把映射写入 `undo_history.json`，`undo` 逆向恢复并清理空目录。

**是否需要大模型？** 只有 `discover-rules`（按内容归纳规则）、`watch-agent`（监听 + 自动出方案）需要；`scan` / `plan` / `apply` / `organize` / `ask` / `undo` / `watch` 全部本地运行。`ask` 用的是「规则匹配 + 槽位抽取」，**不需要 API Key**。

## 用户场景

| 场景 | 需求 | 用哪个 |
|---|---|---|
| 下载文件夹堆积了上百个杂七杂八的文件 | 按类型分门别类 | `organize`（默认管道）或 `ask "按类型整理"` |
| 文档按**主题**混杂（合同、发票、学习资料、报销单…） | 按**内容**而不是扩展名分类 | `discover-rules` + `--rules` |
| 既要按内容分，又要在一级目录下再按格式分 | 两级归档：`内容/格式/文件` | `classify by=content` + `classify by=type mode=append` |
| 手机/相机导出的一堆 `mmexport*.jpg` | 按修改日期排序并重命名 | `sort by=mtime` + `rename "{date}_{index:03d}{suffix}"` |
| 压缩包散落各处 | 统一集中到 `归档/` | `move rule=to_path target=归档` |
| 同一批文件重复拷贝了多份 | 找出并清掉重复 | `dedup` + `filter` + `move` |
| 希望文件一落盘就自动整理 | 常驻监听 | `watch`（本地）/ `watch-agent`（大模型） |
| 整理的目录嵌套很深 | 递归读取且不破坏原结构 | `--preserve-structure` |
| 接入自己的 AI 助手 | 让 Agent 调用整理能力 | `skills/` 或 `integrations/nanobot/` |
| 手滑执行了错误的整理 | 回滚 | `undo --n 1` |

## 功能特性

- **目录扫描**：递归遍历，输出文件清单与元数据（大小 / 修改时间 / 扩展名 / MIME），支持隐藏文件、符号链接、最大深度。
- **三种分类维度**：按扩展名类型、按**文件名**关键词、按**文件内容**关键词。
- **层级分类**：`classify mode=append` 可把两个维度拼成 `内容/格式` 两级目录。
- **批量重命名**：模板化命名，支持日期、时间、序号（可格式化）、原文件名、分类名等占位符，可只对满足条件的文件生效。
- **定向移动与归档**：按条件筛选后移动到指定目录；`preserve=true` 可就地分类而不扁平化。
- **内容去重**：按内容哈希识别重复文件，保留策略可选。
- **标签**：给文件打标签，供后续阶段筛选。
- **计划预览 + 冲突策略**：`skip` / `overwrite` / `rename_suffix`。
- **一键撤销**：按历史栈回滚最近 N 次整理。
- **自动监听**：`watch`（本地、顶层、固定管道）与 `watch-agent`（递归、大模型动态出方案）。
- **大模型自适应分类**：`discover-rules` 让大模型读目录内容，自己归纳主题与关键词。
- **可选依赖优雅降级**：核心零第三方依赖；未装可选库时对应能力给出明确提示。

## 仓库结构

```text
ai-file-organizer/
├── src/file_organizer/          # 核心实现
│   ├── cli.py                   # 命令行入口（8 个子命令）
│   ├── scanner.py               # 目录扫描
│   ├── model.py                 # FileRecord 数据模型
│   ├── pipeline.py              # 声明式 pipeline 的解析与执行
│   ├── stages/                  # 整理原语
│   │   ├── filter.py            #   条件筛选
│   │   ├── classify.py          #   分类（type / name / content）
│   │   ├── sort.py              #   排序
│   │   ├── rename.py            #   批量重命名
│   │   ├── move.py              #   移动 / 归档 / 就地分类
│   │   ├── tag.py               #   打标签
│   │   ├── dedup.py             #   内容去重（标记）
│   │   └── where.py             #   条件表达式 DSL
│   ├── planner.py               # 生成计划与预览
│   ├── executor.py              # 落盘执行与冲突策略
│   ├── undo.py                  # 撤销历史与回滚
│   ├── security.py              # 整理根目录保护
│   ├── rules.py                 # 规则加载（type / name / content）
│   ├── extractors/              # 文本抽取（pdf / docx / pptx / xlsx / doc / 归档）
│   ├── watcher.py               # CLI watch：watchdog 监听
│   ├── agent_watcher.py         # watch-agent：递归监听 + 大模型生成方案
│   ├── agent.py                 # 自然语言 → 意图 → pipeline
│   ├── llm.py                   # OpenAI 兼容客户端（仅标准库 urllib）
│   ├── lowtoken.py              # 计划摘要与 token 估算
│   └── logging_conf.py          # 日志配置
├── scripts/watch_agent.py       # watch-agent 独立启动脚本
├── skills/                      # Agent Skill 说明（SKILL.md + 6 个子 Skill）
├── integrations/nanobot/        # nanobot 格式的 Skill 与部署说明
├── examples/                    # pipeline 与规则示例
│   ├── pipeline_rename_example.json
│   ├── pipeline_full_example.json   # 内容分类→格式分类→图片改名→归档 全流程
│   └── rules_demo.json              # 针对 demo 素材的内容分类规则
├── tests/                       # 测试用例（pytest，22 个测试文件）
├── demo/                        # 测试数据（公开领域素材，扁平未整理）
├── config/rules.yaml            # 人类可读的规则文档
├── DEMO_CREDITS.md              # demo 素材来源与许可
├── .env.example                 # 大模型配置示例（已脱敏）
├── pyproject.toml               # 打包、依赖与可选 extras
├── LICENSE                      # MIT
└── README.md
```

## 安装

### 环境要求

- **Python 3.10+**（使用了 `X | None` 等新语法）
- 操作系统：Windows / macOS / Linux 均可
- **核心功能零第三方依赖**，可选能力按需安装

### 安装方式

```bash
# 1) 获取代码
git clone https://github.com/STAR-LAB-AI-Agent/file-archiving.git
cd file-archiving

# 2) 基础安装（仅核心，无第三方依赖）
pip install -e .

# 3) 或安装全部可选能力
pip install -e ".[content,watch,config,dev]"
```

### 可选依赖（extras）

| extra | 安装内容 | 解锁的能力 |
|---|---|---|
| （无，默认） | 仅标准库 | 扫描 / 分类（类型、文件名）/ 重命名 / 移动 / 去重 / 计划 / 撤销 |
| `content` | `pypdf`、`python-docx` | **按内容分类**（抽取 PDF / DOCX / PPTX / XLSX 文本） |
| `watch` | `watchdog` | `watch` 目录监听 |
| `config` | `pyyaml` | 用 YAML 写规则文件 |
| `dev` | `pytest` | 运行测试 |

### 验证安装

```bash
file_organizer --help          # 查看所有子命令
file_organizer scan --path demo --table
```

安装后会得到两个命令：`file_organizer`（主命令）与 `watch-agent`（递归监听智能体）。

> **注意**：如果你从更早的版本升级，新增的 console script 需要重新执行一次 `pip install -e .` 才会注册。

## 大模型配置（可选）

仅 `discover-rules` 与 `watch-agent` 需要配置，**其他功能完全不需要**。

配置方式一：项目根目录建 `.env`（已被 `.gitignore` 忽略，不会误提交）

```bash
cp .env.example .env        # 然后填入你自己的 Key
```

配置方式二：设置环境变量

```bash
# Linux / macOS
export MODEL_BASE_URL="https://api.deepseek.com/v1"
export MODEL_API_KEY="sk-your-api-key-here"
export MODEL_NAME="deepseek-chat"

# Windows PowerShell
$env:MODEL_BASE_URL="https://api.deepseek.com/v1"
$env:MODEL_API_KEY="sk-your-api-key-here"
$env:MODEL_NAME="deepseek-chat"
```

`.env.example` 内容（**已脱敏，仓库中不含任何真实密钥**）：

```dotenv
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_API_KEY=sk-your-api-key-here
MODEL_NAME=deepseek-chat
```

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MODEL_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容服务的 base URL |
| `MODEL_API_KEY` | 无（必填） | 缺失时 `discover-rules` / `watch-agent` 会明确报错 |
| `MODEL_NAME` | `deepseek-chat` | 模型名；也可用 `--model` 临时覆盖 |

任何 OpenAI 兼容服务都可以用（换 `MODEL_BASE_URL` 与 `MODEL_NAME` 即可）。

> **`.env` 是按「当前工作目录」的相对路径加载的**，不是按包安装目录。所以请在含 `.env` 的目录下启动 `watch-agent`，否则请改用环境变量。

## 快速开始

```bash
# 1) 看看目录里有什么（不写盘）
file_organizer scan --path demo --table

# 2) 一键整理：先预览计划
file_organizer organize --path demo --dry-run

# 3) 确认无误后执行
file_organizer organize --path demo --yes

# 4) 用自然语言（本地意图识别，无需 API Key）
file_organizer ask "按类型整理" --path demo --yes

# 5) 后悔了：一键撤销
file_organizer undo --path demo
```

> `demo/` 是一份刻意保持扁平的公开素材，放心反复试跑；弄乱了可以用 `git checkout -- demo/ && git clean -fd demo/` 还原。

## 命令行参考

| 子命令 | 说明 | 是否写盘 | 是否需大模型 |
|---|---|---|---|
| `scan` | 扫描目录，输出结构化文件清单 | 否 | 否 |
| `plan` | 扫描 + 管道 → 生成计划/预览 | 否 | 否 |
| `apply` | 执行 `plan.json` | **是** | 否 |
| `organize` | 一键全流程：scan → pipeline → plan →（确认后）apply | 可选 | 否 |
| `ask` | 自然语言指令 → 意图识别 → 管道 → 计划/执行 | 可选 | 否 |
| `undo` | 一键撤销最近 N 次整理 | **是** | 否 |
| `watch` | 监听目录，新文件自动整理 | 是 | 否 |
| `discover-rules` | 用大模型从目录内容归纳分类规则 | 否（只输出规则） | **是** |

### `scan` — 扫描目录

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 要扫描的目录路径 |
| `--no-recursive` | 关 | 不递归子目录 |
| `--include-hidden` | 关 | 包含隐藏文件 |
| `--follow-symlinks` | 关 | 把符号链接文件纳入结果 |
| `--max-depth` | 无限制 | 递归最大深度 |
| `--table` | 关 | 以表格输出（默认 JSON） |

```bash
file_organizer scan --path demo --table
file_organizer scan --path demo --no-recursive --include-hidden
file_organizer scan --path demo --max-depth 2 > manifest.json
```

### `plan` — 生成计划（不落盘）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 要整理的目录 |
| `--pipeline` | 默认管道 | pipeline JSON 文件路径 |
| `--rules` | 无 | 内容分类规则文件（JSON/YAML） |
| `--preserve-structure` | 关 | 就地分类，保留嵌套目录结构（不扁平化） |
| `--output` | 无 | 把 `plan.json` 保存到该路径，供 `apply` 使用 |

```bash
file_organizer plan --path demo
file_organizer plan --path demo --pipeline examples/pipeline_full_example.json \
                    --rules examples/rules_demo.json --output plan.json
```

### `apply` — 执行计划（落盘）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--plan` | 必填 | `plan.json` 文件路径 |
| `--conflict` | `skip` | 冲突策略：`skip` / `overwrite` / `rename_suffix` |
| `--only` | 无 | 只执行这些 action id（逗号分隔） |
| `--exclude` | 无 | 跳过这些 action id（逗号分隔） |
| `--dry-run` | 关 | 只模拟，不落盘 |

```bash
file_organizer apply --plan plan.json
file_organizer apply --plan plan.json --conflict rename_suffix
file_organizer apply --plan plan.json --only a001,a002
file_organizer apply --plan plan.json --dry-run
```

### `organize` — 一键全流程

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 要整理的目录 |
| `--pipeline` | 默认管道 | pipeline JSON 文件路径 |
| `--rules` | 无 | 内容分类规则文件 |
| `--preserve-structure` | 关 | 就地分类，保留嵌套结构 |
| `--conflict` | `skip` | 冲突策略 |
| `--yes` | 关 | 确认并执行（不加则只预览） |
| `--dry-run` | 关 | 只生成计划，不执行 |

```bash
file_organizer organize --path demo --dry-run
file_organizer organize --path demo --yes
file_organizer organize --path demo --preserve-structure --yes
```

默认管道 = `classify(by=type)` → `move(by_category)`。

### `ask` — 自然语言入口

用**规则匹配 + 槽位抽取**把中文指令翻译成 pipeline，**无需大模型**。

| 参数 | 默认 | 说明 |
|---|---|---|
| `instruction` | 必填 | 自然语言指令（位置参数） |
| `--path` | 必填 | 要整理的目录 |
| `--rules` | 无 | 内容分类规则文件 |
| `--preserve-structure` | 关 | 就地分类 |
| `--conflict` | `skip` | 冲突策略 |
| `--yes` | 关 | 确认并执行 |
| `--dry-run` | 关 | 只生成计划 |

```bash
file_organizer ask "按类型整理" --path demo --yes
file_organizer ask "重命名为 {date}_{index:03d}{suffix}" --path demo --yes
file_organizer ask "移到 归档" --path demo --yes
file_organizer ask "找出重复文件" --path demo --yes
file_organizer ask "按内容分类" --path demo --rules examples/rules_demo.json --preserve-structure --yes
```

识别成功后会回显 `指令 / 意图 / 管道`，便于确认它理解得对不对。

### `undo` — 一键撤销

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 目标目录（用于定位撤销历史） |
| `--n` | `1` | 回滚最近 N 次整理 |

```bash
file_organizer undo --path demo
file_organizer undo --path demo --n 3
```

### `watch` — 监听目录（本地）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 要监听的目录（**仅顶层**） |
| `--pipeline` | 默认管道 | pipeline JSON 文件路径 |
| `--debounce` | `2.0` | 防抖秒数 |
| `--conflict` | `skip` | 冲突策略 |
| `--dry-run` | 关 | 只预览，不落盘 |

```bash
file_organizer watch --path demo
file_organizer watch --path demo --pipeline examples/pipeline_full_example.json
```

> `watch` **没有** `--rules` 参数，因此使用 `classify by=content` 的管道在它下面会报错。需要内容分类的自动整理请用 [`watch-agent`](#监听与自动化)。

### `discover-rules` — 大模型归纳内容规则

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 要分析的目录 |
| `--output` | 无 | 把规则保存为 JSON 文件 |
| `--max-files` | `15` | 采样文件数上限 |
| `--max-chars` | `400` | 每个文件摘要长度上限 |
| `--per-file-chars` | 等于 `--max-chars` | 每个样本实际携带的字符数 |
| `--default-folder` | `其他` | 未命中任何主题时的兜底目录 |

```bash
file_organizer discover-rules --path demo --output rules.json
file_organizer discover-rules --path demo --max-files 55 --per-file-chars 260 --output rules.json
```

**采样量直接影响质量**：采样太少会漏掉目录中的次要主题，导致大量文件落进兜底目录。经验上建议 `--max-files` 覆盖目录中**有文本文件的大多数**。

## Pipeline 与整理原语

整理能力由声明式 pipeline 描述，各 stage **顺序执行**、可任意组合：

```json
{
  "stages": [
    {"op": "classify", "by": "type"},
    {"op": "move", "rule": "by_category"}
  ]
}
```

### Stage 清单

| stage | 作用 | 参数 |
|---|---|---|
| `filter` | 按条件筛选，**永久移除**不满足条件的记录 | `where` |
| `classify` | 分类，写入 `category` 字段（不落盘） | `by` ∈ {`type`,`name`,`content`}；`mode` ∈ {`overwrite`,`append`}；`where` |
| `sort` | 排序（影响后续 `rename` 的序号） | `by` ∈ {`name`,`size`,`mtime`,`type`,`category`}；`order` ∈ {`asc`,`desc`} |
| `rename` | 按模板重命名 | `template`；`where`；`index_start`（默认 `1`） |
| `move` | 计算目标目录 | `rule` ∈ {`by_category`,`to_path`}；`target`；`preserve`（默认 `false`）；`where` |
| `tag` | 给文件打标签 | `tags`；`where` |
| `dedup` | 按内容哈希去重，**只标记** | `by`=`content_hash`；`keep`（默认 `first`） |

### 条件表达式（where）

```text
where := {"field","op","value"}
       | {"and": [where, ...]}
       | {"or":  [where, ...]}
       | {"not": where}

field ∈ {name, stem, suffix, extension, mime_type, size, mtime, mtime_days,
         category, tags, is_kept}
op    ∈ {eq, ne, in, not_in, gt, gte, lt, lte, contains, startswith, endswith, regex}
```

示例——「扩展名是 pdf 或 docx，且大于 10MB」：

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
| `{suffix}` | 扩展名（**含**点） | `.pdf` |
| `{ext}` | 扩展名（**不含**点） | `pdf` |
| `{category}` | 分类名 | `文档` |
| `{index}` | 序号，可格式化 `{index:03d}` | `001` |

### 复合示例：内容分类 → 格式分类 → 图片按时间改名 → 压缩包归档

`examples/pipeline_full_example.json`（可直接运行，见下方实测输出）：

```json
{
  "stages": [
    {"op": "classify", "by": "content"},
    {"op": "classify", "by": "type", "mode": "append"},
    {"op": "sort", "by": "mtime", "order": "asc"},
    {"op": "rename", "template": "{date}_{index:03d}{suffix}",
     "where": {"field": "category", "op": "endswith", "value": "图片"}},
    {"op": "move", "rule": "to_path", "target": "归档",
     "where": {"field": "category", "op": "endswith", "value": "压缩包"}},
    {"op": "move", "rule": "by_category",
     "where": {"not": {"field": "category", "op": "endswith", "value": "压缩包"}}}
  ]
}
```

运行：

```bash
file_organizer organize --path demo \
  --pipeline examples/pipeline_full_example.json \
  --rules examples/rules_demo.json --dry-run
```

实测输出（`demo/` 的 12 个文件）：

```text
学术论文\文档\arxiv-论文.pdf
生物学经典\文档\物种起源.txt
文学名著\文档\爱丽丝梦游仙境.txt
演示文稿\演示\幻灯片.pptx
演示文稿\演示\演示文稿.pptx
示例文档\文档\示例文档.docx
电子表格\表格\销售图表.xlsx
其他\图片\2026-09-19_001.png      ← 图片无正文，按内容分类落入兜底，再被排序改名
其他\图片\2026-09-19_002.jpg
其他\图片\2026-09-19_003.jpg
其他\图片\2026-09-19_004.jpg
归档\示例归档.zip
```

> **「组合即语义」**：`sort` 必须在 `rename` **之前**，序号才会按时间递增；`classify` 用 `mode=append` 才能形成层级（`内容类/格式类`）；最后一步用 `where` 的 `not` 把已归档的压缩包排除，避免重复移动。

## 内容分类规则

`classify(by=content)` 会抽取文件文本（默认前 512 字符），再按关键词子串匹配（大小写不敏感）。

> **本工具不内置任何内容规则。** 写死的通用规则（如「合同 / 发票 / 简历」）会误命中无关文档
> （例如含「教育背景」的文件被判成简历），所以关键词必须由调用方根据目录**实际内容**提取后提供；
> 未提供时 `classify(by=content)` 会**直接报错**并给出指引。

两种获取规则的方式：

**方式一：让模型自己提取（推荐）**

通读目录里的文件，提炼 3–8 个主题、每个主题 3–8 个**有区分度**的关键词，写成：

```json
{
  "content_rules": {
    "学术论文": ["Google hereby grants permission", "Attention Is All You Need"],
    "文学名著": ["Alice's Adventures in Wonderland"]
  },
  "default_folder": "其他"
}
```

然后用 `--rules rules.json` 传入。

**方式二：让工具调用模型提取**

```bash
file_organizer discover-rules --path <目录> --output rules.json
```

规则文件支持 **JSON**（无额外依赖）与 **YAML**（需 `config` extra）。可用字段：

| 字段 | 说明 |
|---|---|
| `type_rules` | 扩展名 → 分类目录名 |
| `name_rules` | 文件名关键词 → 分类目录名 |
| `content_rules` | 内容关键词 → 分类目录名 |
| `default_folder` | 未命中任何规则时的兜底目录（默认 `其他`） |

**关键词选择的两个经验：**

1. **不要用文件名当关键词**——`classify(by=content)` 只匹配正文，文件名里的词往往不在正文中（图片、扫描件更没有正文）。
2. **避免过于宽泛的词**——比如用 `arXiv` 做关键词，会让「提到过 arXiv 的说明文档」也被判成学术论文。关键词越具体，误判越少。

`examples/rules_demo.json` 是一份可直接运行的示例（关键词全部取自 demo 素材的真实正文）。

## 作为 Agent Skill 使用

`skills/` 目录定义了一组可供智能体调用的能力说明，每条 Skill 最终映射到 `file_organizer` 的某个子命令：

```text
自然语言 → 意图识别/参数抽取 → Skill → file_organizer CLI → pathlib/watchdog → 结果
```

| Skill | 触发场景 | 对应子命令 |
|---|---|---|
| [`organize`](skills/organize.md) | 一键全流程整理 | `organize` / `ask` |
| [`classify`](skills/classify.md) | 分类整理 | `plan` + `apply` |
| [`rename`](skills/rename.md) | 批量重命名 | `plan` + `apply` |
| [`move`](skills/move.md) | 定向移动 / 归档 | `plan` + `apply` |
| [`watch`](skills/watch.md) | 自动监听 | `watch` |
| [`undo`](skills/undo.md) | 一键撤销 | `undo` |

通用约定（详见 [`skills/SKILL.md`](skills/SKILL.md)）：

- **预览优先**：任何写 / 移动 / 重命名操作前，必须先 `plan` 回显预览，确认后才 `apply`。
- **结构化返回**：结果统一为 JSON，便于程序消费。
- **目录保护**：仅在用户显式指定的根目录内操作，拒绝操作系统目录。

## 作为 nanobot Skill 使用

`integrations/nanobot/` 下提供符合 [nanobot](https://github.com/HKUDS/nanobot) 规范的 Skill（`<workspace>/skills/<name>/SKILL.md` + YAML frontmatter），可直接被 Agent Runtime 加载：

```bash
# 1) 把 skill 复制到 nanobot 的 workspace（默认 ~/.nanobot/workspace）
mkdir -p ~/.nanobot/workspace/skills
cp -r integrations/nanobot/skills/ai-file-organizer ~/.nanobot/workspace/skills/

# 2) 确保 file_organizer 在该 runtime 的 PATH 上
pip install -e .

# 3) 启动 nanobot，直接用自然语言提需求
nanobot -m "把 ~/Downloads 这个文件夹按类型整理好"
```

nanobot 会读取 `SKILL.md`、遵循「先预览、确认后执行」的约定，并调用 `file_organizer` 完成整理。详见 [`integrations/nanobot/README.md`](integrations/nanobot/README.md)，其中还包含 pipeline 细节与常见坑（如 `dedup` 只标记不移动）。

## 监听与自动化

两条监听路线，按是否需要「按内容分类」选择：

| | `watch-agent`（推荐） | `watch` |
|---|---|---|
| 监听范围 | **递归**（含所有子目录） | 仅顶层 |
| 触发时做什么 | 通知**大模型**现场生成整理方案 | 跑固定管道 |
| 支持内容分类 | ✅（大模型直接生成规则/管道） | ❌（没有 `--rules`） |
| 依赖 | DeepSeek 等 OpenAI 兼容 API | `watchdog` |
| 命令 | `watch-agent` / `python scripts/watch_agent.py` | `file_organizer watch` |

### 启动 watch-agent

```bash
# 先干跑，只看方案不落盘
watch-agent --path <目录> --dry-run

# 正式启动（Ctrl+C 停止）
watch-agent --path <目录>
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--path` | 必填 | 监听目录（递归，含所有末端子目录） |
| `--debounce` | `5.0` | 变动静默多少秒后触发（合并批量落盘，避免频繁调用 API） |
| `--cooldown` | `2.0` | 整理后冷却秒数，防止整理自身事件造成回环 |
| `--conflict` | `skip` | 冲突策略 |
| `--dry-run` | 关 | 只让大模型给方案并预览，不落盘 |
| `--model` | 读配置 | 覆盖 `MODEL_NAME` |

流程：

```text
文件变动 → 静默 debounce 秒 → 调用大模型生成 pipeline → 执行整理 → 写撤销日志
```

实测日志：

```text
监听目录（递归）：.../demo
静默 5.0s 后触发大模型；按 Ctrl+C 停止。

[变动] 检测到 1 个文件发生变化
[大模型] 整理方案：classify → move
[执行] applied=3 skipped=0 failed=0
```

> 注意：`watch-agent` 触发时会针对**整个监听根目录**重新生成方案，不只处理新落盘的那个文件。若只想动新文件，请在管道中用 `where` 收窄条件。

## 安全与撤销

- **计划预览**：任何改动前先产出计划，默认不落盘；`organize` 不加 `--yes` 只预览。
- **目录保护**：`assert_safe_root` 拒绝把操作系统目录（如 `C:\Windows`、`/`）作为整理根目录。
- **边界约束**：目标默认必须位于整理根目录内；`move rule=to_path` 使用**绝对路径**时才允许显式跨目录移动。
- **冲突处理**：同名目标默认 `skip`（跳过），可选 `overwrite` 或 `rename_suffix`（加后缀）。
- **一键撤销**：每次执行把 `source → target` 映射写入 `<根目录>/.file_organizer/undo_history.json`，`undo` 逆向恢复并清理产生的空目录。

```bash
file_organizer undo --path demo --n 1     # 回滚最近一次
```

> 撤销依赖 history 栈：若手动删除了 `.file_organizer/undo_history.json`，则无法回滚。

## 测试数据（demo/）

`demo/` 是**刻意保持扁平、未整理**的样本目录，覆盖多种格式，用于体验按类型 / 按内容整理：

```text
demo/
├── 物种起源.txt          Project Gutenberg（公共领域）
├── arxiv-论文.pdf        arXiv:1706.03762（开放获取）
├── 星系照片.jpg          Wikimedia Commons / NASA·ESA（公共领域）
├── 爱丽丝梦游仙境.txt     Project Gutenberg（公共领域）
├── 蒙娜丽莎.jpg          Wikimedia Commons（公共领域）
├── 星空.jpg              Wikimedia Commons（公共领域）
├── 演示文稿.pptx         python-pptx 测试文件（MIT）
├── 幻灯片.pptx           python-pptx 测试文件（MIT）
├── 示例文档.docx         python-docx 测试文件（MIT）
├── 图片.png              python-docx 测试文件（MIT）
├── 销售图表.xlsx         Apache POI 测试数据（Apache-2.0）
└── 示例归档.zip          由本目录公共领域文本打包生成
```

全部素材均为**公共领域或宽松开源许可**，来源逐条记录在 [`DEMO_CREDITS.md`](DEMO_CREDITS.md)，**不含任何真实个人信息**。

试跑后若要还原：

```bash
git checkout -- demo/ && git clean -fd demo/
```

> 用自己的目录测试时，请不要把含个人隐私或敏感信息的文件提交到仓库。

## 测试方法

```bash
# 运行全部测试（pyproject 已设 addopts=-q）
pytest

# 详细输出
pytest -v

# 只跑某个模块
pytest tests/test_stages_rename.py -v

# 显示跳过原因
pytest -rs
```

当前状态：**104 passed, 2 skipped**（约 0.6 秒）。

| 测试文件 | 覆盖内容 |
|---|---|
| `test_scanner.py` | 递归扫描、隐藏文件、符号链接、权限位、深度限制 |
| `test_pipeline.py` | pipeline 解析、stage 串联、规则注入 |
| `test_stages_*.py` | 每个整理原语的独立单测（filter/classify/sort/rename/move/tag/dedup） |
| `test_planner.py` | 计划生成、action id、预览渲染 |
| `test_executor.py` | 落盘执行、冲突策略、选择性执行 |
| `test_undo.py` | 撤销历史、多轮回滚、空目录清理 |
| `test_security.py` | 整理根目录保护、越界目标拦截 |
| `test_rules.py` | 规则加载（JSON/YAML/BOM）、无内容规则时报错 |
| `test_extractors.py` | PDF / DOCX / PPTX / XLSX 文本抽取 |
| `test_agent.py` | 自然语言意图识别与槽位抽取 |
| `test_agent_watcher.py` | 变动收集、防抖、prompt 构造、回环防护 |
| `test_theme.py` | 文件采样、规则 JSON 解析、内容规则发现 |
| `test_lowtoken.py` | 计划摘要与 token 估算 |
| `test_watcher.py` | 监听触发过滤（忽略整理自身产生的事件） |
| `test_organize_e2e.py` | 端到端：扫描 → 管道 → 计划 → 执行 |

2 项跳过的原因（Windows 平台限制，非缺陷）：

```text
SKIPPED tests/test_scanner.py:120: POSIX 权限位在 Windows 上不生效
SKIPPED tests/test_scanner.py:135: 创建符号链接在 Windows 上需额外权限
```

## 已知问题与限制

### 分类相关

1. **内容分类只读正文，不含文件名**：`classify(by=content)` 抽取正文前 512 字符做匹配。因此正文稀疏或无正文的文件（图片、音频、扫描件、日程表、签到表）会落进兜底目录 `其他`。
   缓解：在内容分类之后补一段名称分类，并且只作用于兜底目录——

   ```json
   {"op": "classify", "by": "name",
    "where": {"field": "category", "op": "eq", "value": "其他"}}
   ```

   （`name` 分类读取 `name_rules`，可在规则文件的 `name_rules` 字段里自定义。）
2. **不做 OCR**：图片、扫描版 PDF 无文本层，无法参与内容分类。
3. **内容分类必须自带规则**：不提供规则时直接报错，这是有意设计（避免用写死规则瞎猜），不是故障。
4. **关键词过宽会误判**：如 `arXiv`、`docx` 这类词会让说明文档也被归入对应主题。关键词应尽量具体。
5. **`discover-rules` 的效果取决于采样量**：`--max-files` 太小会漏掉次要主题，导致大量文件落兜底目录。

### 监听相关

6. **`watch` 不支持 `--rules`**：使用 `classify by=content` 的管道在 `watch` 下会报错；需要内容分类的自动整理请用 `watch-agent`。
7. **`watch` 只监听顶层**（非递归），且用非递归扫描避免重复处理已整理的子目录。
8. **`watch-agent` 会重排整个根目录**：触发时大模型看到的是目录现状，因此可能移动不只一个新文件。

### 原语语义

9. **`{index}` 是阶段内全局计数器**（从 `index_start` 起），**不按日期分组重置**。同一天多张图片序号连续；跨日期不会重新从 `001` 开始。
10. **`filter` 是永久移除**：被过滤掉的记录不再参与后续任何 stage（不会移动文件）。只想对某类文件施加某个操作时，应使用该 stage 自己的 `where`，而不是先 `filter` 再操作。
11. **`move rule=by_category` 默认扁平化**：默认会把文件直接放到分类目录下，丢弃原有嵌套结构；要保留结构须加 `preserve=true`（CLI 为 `--preserve-structure`）。
12. **`dedup` 只标记不移动**：它只写入 `is_kept` / `dup_group`，必须再接 `filter(is_kept=false)` + `move` 才会真正移走重复文件。

### 运行与配置

13. **`.env` 按当前工作目录的相对路径加载**，不是包安装目录。在别处启动 `watch-agent` 会报「缺少 MODEL_API_KEY」。
14. **大模型调用是同步阻塞的**，`discover-rules` / `watch-agent` 期间没有并发度；`watch-agent` 仅用 busy 标志 + 冷却时间防止自身事件造成回环。
15. **升级后 console script 需重新 `pip install -e .`** 才会注册（本地 editable 安装的常见现象）。
16. **撤销依赖 history 栈**：手动删除 `.file_organizer/undo_history.json` 后无法回滚；本项目**不使用回收站**，落盘即真实移动。
17. **PDF 抽取依赖文本层**：加密或扫描版 PDF 抽不到文本；`pypdf` 对结构异常的 PDF 会向 stderr 输出 `Ignoring wrong pointing object` 之类的告警，属正常现象，不影响结果。

### 尚未实现

18. OCR 图片文字识别；音视频内容识别；跨设备/跨盘移动；按内容相似度（而非哈希）去重；GUI 界面。

## 开源依赖与许可证

### 运行时依赖

| 库 | 许可证 | 用途 | 是否必需 |
|---|---|---|---|
| `pathlib` / `mimetypes` / `argparse` / `urllib` / `hashlib` 等 | PSF-2.0（Python 标准库） | 核心文件操作、CLI、HTTP | 必需（随 Python 提供） |
| `watchdog` | Apache-2.0 | 目录监听（`watch`） | 可选（`watch` extra） |
| `pypdf` | BSD-3-Clause | PDF 文本抽取 | 可选（`content` extra） |
| `python-docx` | MIT | DOCX 文本抽取 | 可选（`content` extra） |
| `pyyaml` | MIT | YAML 规则文件加载 | 可选（`config` extra） |
| `pytest` | MIT | 测试框架 | 仅开发（`dev` extra） |

核心功能**仅依赖 Python 标准库**，不引入任何强制第三方依赖。

### 测试数据许可

`demo/` 下素材来自 Project Gutenberg（公共领域）、Wikimedia Commons（公共领域）、arXiv（开放获取）、python-docx / python-pptx（MIT）、Apache POI（Apache-2.0）。逐条记录见 [`DEMO_CREDITS.md`](DEMO_CREDITS.md)。

## License

本项目采用 [MIT](LICENSE) 许可证。

[MIT](LICENSE) © 2026 赵旭东 · [@violet-041125](https://github.com/violet-041125)
