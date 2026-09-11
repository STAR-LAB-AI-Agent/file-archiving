# Skill 总览：文件智能整理

本目录定义可供智能体调用的「文件整理」能力。每个 Skill 最终调用 `file_organizer` CLI 的对应子命令（CLI 可独立运行、独立测试）。

## 调用链

```
自然语言 → 意图识别/参数抽取 → Skill → file_organizer CLI → pathlib/watchdog → 结果
```

## 子 Skill 一览

| Skill | 触发场景 | 子命令 |
|---|---|---|
| [organize](organize.md) | 一键全流程整理 | `organize` / `ask` |
| [classify](classify.md) | 分类整理 | `plan` + `apply` |
| [rename](rename.md) | 批量重命名 | `plan` + `apply` |
| [move](move.md) | 定向移动 / 归档 | `plan` + `apply` |
| [watch](watch.md) | 自动监听 | `watch` |
| [undo](undo.md) | 一键撤销 | `undo` |

## 通用约定

- **预览优先**：任何写 / 移动 / 重命名操作前，必须先 `plan` 回显预览，确认后才 `apply`。
- **结构化返回**：结果统一为 JSON，便于程序消费。
- **目录保护**：仅在用户显式指定的根目录内操作，拒绝操作系统目录。
- **自然语言入口**：`file_organizer ask "<指令>" --path <目录> [--yes | --dry-run]`。
