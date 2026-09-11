# Skill: classify（分类整理）

## 使用场景
用户想把文件按**类型 / 文件名 / 内容**分到不同子目录。

## 触发示例
- 「按文件类型整理到子文件夹」
- 「按文件名把这些 PDF 分类」
- 「按内容把文档分成合同 / 发票 / 简历」（内容维度）

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 目标目录 |
| by | enum | 否 | type | 分类维度：type / name / content |

## 调用方式

```bash
# 预览（pipeline：classify → move by_category）
file_organizer plan --path <path> --pipeline pipeline.json
# 执行
file_organizer apply --plan plan.json

# 自然语言入口
file_organizer ask "按文件名分类" --path <path> --yes
```

## 结果格式

`plan.json`（含 summary 与逐条 actions）+ apply 结果 JSON（applied / skipped / failed）。

## 示例

### 示例 1
- 用户：「按文件类型整理」
- 管道：`classify(by=type) → move(by_category)`
- 结果：`a.pdf → 文档/`、`b.jpg → 图片/`、`c.xyz → 其他/`。

### 示例 2
- 用户：「按文件名分类」
- 管道：`classify(by=name) → move(by_category)`
- 结果：文件名含「合同」→ 合同/，含「发票」→ 发票/，其余 → 其他/。
