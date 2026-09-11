# nanobot 集成

把 ai-file-organizer 作为 **nanobot Skill** 加载与调用。以下步骤已实测通过。

## nanobot 的 Skill 约定

- 路径：`<workspace>/skills/<name>/SKILL.md`（默认 workspace 为 `~/.nanobot/workspace`）
- `SKILL.md` 必须带 YAML frontmatter：`name`（须与目录名完全一致，小写+连字符）、`description`（1–1024 字符）
- 可选 `metadata.nanobot.requires.{bins,env}` 声明依赖；缺失时该 skill 被标为 *unavailable*
- 采用**渐进式加载**：先把 name+description 摘要注入上下文，agent 需要时再读完整 `SKILL.md`

```
integrations/nanobot/
└── skills/
    └── ai-file-organizer/
        ├── SKILL.md                 # frontmatter + 指令
        └── references/
            └── pipeline.md          # pipeline DSL 详细参考（按需加载）
```

## 部署步骤（实测）

### 1. 准备一个装了 nanobot 与 file_organizer 的环境

```powershell
# 建独立 venv（Python 3.11+）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装 nanobot（PyPI 稳定版；源码安装需要额外装 Bun）
pip install nanobot-ai

# 把 file_organizer 装进同一环境（可编辑安装，便于同步改动）
pip install -e <path-to-ai-file-organizer>
```

> 两者装进同一 venv，`nanobot` 与 `file_organizer` 都会出现在该 venv 的 `Scripts/`。
> **启动 nanobot 前务必先激活该 venv**（或把 `Scripts` 加到 PATH），否则
> `requires.bins: [file_organizer]` 检查失败，skill 会显示 unavailable。

### 2. 配置模型

`~/.nanobot/config.json`（示例接 DeepSeek）：

```json
{
  "providers": {
    "deepseek": { "apiKey": "sk-xxx", "apiBase": "https://api.deepseek.com/v1" }
  },
  "modelPresets": {
    "primary": { "provider": "deepseek", "model": "deepseek-chat",
                 "maxTokens": 4096, "contextWindowTokens": 65536, "temperature": 0.1 }
  },
  "agents": { "defaults": { "modelPreset": "primary" } }
}
```

### 3. 部署 skill

```powershell
$ws = "$HOME\.nanobot\workspace"
New-Item -ItemType Directory -Force "$ws\skills" | Out-Null
Copy-Item -Recurse -Force ".\skills\ai-file-organizer" "$ws\skills\"
```

### 4. 验证

```powershell
nanobot --version
# 启动后说一句自然语言即可，例如：
nanobot -m "把 C:\Users\me\Downloads 这个文件夹按类型整理好"
```

## 实测效果（一次真实运行）

用户指令：*"请用 file_organizer 把 …\nanobot_test 这个文件夹按文件类型分类整理好，我已确认，请直接执行"*

nanobot 的动作序列：

1. `read skills/ai-file-organizer/SKILL.md` —— 读取 skill（渐进式加载生效）
2. `ls <目标目录>` —— 查看待整理文件
3. `$ file_organizer organize --path "…" --dry-run` —— **遵循 skill 的「先预览」规则**
4. `$ file_organizer organize --path "…" --yes` —— 确认后执行
5. `ls <目标目录>` —— 验证结果
6. 汇报：6 个文件全部按类型归入 `文档/ 图片/ 演示/ 表格/`，0 跳过、0 失败、0 冲突

## 使用方式

启动 nanobot 后，**直接用自然语言**即可（nanobot 按 `description` 自动匹配该 skill）：

```
把这个文件夹整理好：C:\Users\me\Downloads
把 D:\photos 里的图片按拍摄日期重命名
找出 D:\docs 里的重复文件
```

也可以用 `$skill-name` **显式调用**：

```
$ai-file-organizer 帮我把 D:\docs 下 90 天没动过的 PDF 移到「归档」
```

WebUI 的 **Skills** 页可看到 `ai-file-organizer` 及其可用状态。
