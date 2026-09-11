# Skill: watch（自动监听）

## 使用场景
用户希望某个「收件箱」目录出现新文件时自动按规则整理，无需手动触发。

## 状态
✅ 可用（可选功能）。底层使用 `watchdog`（Apache-2.0）。

## 触发示例
- 「帮我监听『下载』文件夹，新文件自动整理」
- 「监听收件箱，按类型自动分类」
- 「监听这个目录，但先预览不要真的移动」

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 监听目录（仅顶层新文件触发） |
| pipeline | string | 否 | 默认管道 | pipeline JSON 文件路径 |
| debounce | float | 否 | 2.0 | 防抖秒数（连续事件合并为一次整理） |
| conflict | enum | 否 | skip | skip / overwrite / rename_suffix |
| dry-run | bool | 否 | false | 只预览不落盘 |

## 调用方式

```bash
# 启动监听（Ctrl+C 停止）
file_organizer watch --path <path>

# 自定义管道 + 防抖
file_organizer watch --path <path> --pipeline pipeline.json --debounce 3.0

# 只预览
file_organizer watch --path <path> --dry-run
```

## 结果格式

每次触发输出一行摘要：

```text
[watch] applied=3 skipped=0 failed=0
```

## 安全说明
- 仅监听用户显式指定的目录，拒绝操作系统目录（如 `C:\Windows`）。
- 自动动作写入结构化日志（路径与操作类型，不含敏感信息）。
- 只处理顶层新文件（非递归），避免把已整理子目录反复处理。
- 默认冲突策略 `skip`（最安全）。

## 示例

### 示例 1
- 用户：「监听『下载』文件夹」
- 调用：`file_organizer watch --path 下载`
- 结果：向「下载」放入 `report.pdf`，约 2 秒后自动移入「文档/」。

### 示例 2
- 用户：「监听收件箱，先预览」
- 调用：`file_organizer watch --path 收件箱 --dry-run`
- 结果：放入新文件时只输出计划摘要，不落盘；确认后去掉 `--dry-run` 重跑。
