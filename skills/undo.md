# Skill: undo（一键撤销）

## 使用场景
用户整理后发现误操作，希望撤销最近一次（或第 N 次）整理，恢复到整理前状态。

## 状态
✅ 可用。每次 apply 都会把「源 ↔ 目标」映射写入 `<root>/.file_organizer/undo_history.json`（history 栈），undo 逆向恢复并清理空目录。

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 目标目录（定位 undo_history.json） |
| n | int | 否 | 1 | 回滚最近 N 次 |

## 调用方式

```bash
file_organizer undo --path <path>          # 撤销最近一次
file_organizer undo --path <path> --n 2    # 回滚最近 2 次
```

## 结果格式

```jsonc
{"undone": 3, "failed": [], "remaining_sessions": 0}
```

## 示例

### 示例 1
- 用户：「撤销刚才的整理」
- 调用：`file_organizer undo --path <目录>`
- 结果：文件恢复到整理前位置，空分类目录被清理。

### 示例 2
- 用户：「回滚最近 2 次整理」
- 调用：`file_organizer undo --path <目录> --n 2`
- 结果：最近 2 次整理被逆向恢复。
