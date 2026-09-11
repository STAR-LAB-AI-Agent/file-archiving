# Skill: move（定向移动 / 归档）

## 使用场景
用户想把满足条件的文件**移动到指定目录**，或按分类归档。

## 触发示例
- 「把所有 `.pdf` 移到『文档/PDF』」
- 「把 90 天没改动的文件移到『归档』」
- 「把这些文件归档」

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 目标目录 |
| target | string | 否 | — | 目标目录（未指定则按分类归档） |
| where | object | 否 | — | 筛选条件（字段 + 比较 + and/or） |

## 调用方式

```bash
# 预览
file_organizer plan --path <path> --pipeline move.json
# 执行
file_organizer apply --plan plan.json

# 自然语言入口
file_organizer ask "移到 归档" --path <path> --yes
```

## 结果格式

`plan.json`（op=move 的 actions）+ apply 结果 JSON。

## 示例

### 示例 1
- 用户：「把所有 `.pdf` 移到『文档/PDF』」
- 管道：`filter(extension==pdf) → move(to_path=文档/PDF)`
- 结果：所有 PDF 移动到 文档/PDF/。

### 示例 2
- 用户：「把 90 天没改动的移到『归档』」
- 管道：`filter(mtime_days>90) → move(to_path=归档)`
- 结果：超过 90 天未修改的文件移动到 归档/。
