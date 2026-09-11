# Skill: organize（一键全流程整理）

## 使用场景
用户希望「把某个文件夹整理好」且未指定具体动作，或希望一步完成「分类 + 移动」。

## 触发示例
- 「把『下载』文件夹整理好」
- 「按类型整理桌面」
- 「把照片按日期重命名并归档」（需自定义 pipeline）

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 要整理的目录（绝对或相对路径） |
| conflict | enum | 否 | skip | 冲突策略：skip / overwrite / rename_suffix |

## 调用方式

```bash
# 只预览计划（不落盘）
file_organizer organize --path <path> --dry-run

# 确认并执行
file_organizer organize --path <path> --yes

# 自然语言入口
file_organizer ask "按类型整理" --path <path> --yes
```

默认管道：`classify(按类型) → move(按分类目录)`。

## 结果格式

```jsonc
{
  "summary": {"applied": 6, "skipped": 0, "failed": 0},
  "applied": [{"source": "...", "target": "...", "op": "move"}],
  "skipped": [],
  "failed": []
}
```

## 示例

### 示例 1
- 用户：「把『下载』文件夹整理好」
- 调用：`file_organizer organize --path 下载 --yes`
- 结果：按扩展名把文件分入 文档 / 图片 / 表格 / 视频 / 其他 等子目录。

### 示例 2
- 用户：「把桌面按类型整理」
- 调用：`file_organizer organize --path 桌面 --dry-run`
- 结果：先输出计划预览（列出每个文件 源 → 目标），用户确认后加 `--yes` 执行。
