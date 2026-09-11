# Skill: rename（批量重命名）

## 使用场景
用户想按**模板 / 序号 / 日期**批量重命名文件（原地改名，不移动）。

## 触发示例
- 「把图片重命名为 `2026-07-XX_001` 格式」
- 「给这些 PDF 加上日期前缀」
- 「重命名为 `{date}_{index:03d}{suffix}`」

## 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| path | string | 是 | — | 目标目录 |
| template | string | 是 | — | 命名模板，支持 `{date}` `{time}` `{stem}` `{name}` `{suffix}` `{ext}` `{category}` `{index}` |

## 调用方式

```bash
# 预览
file_organizer plan --path <path> --pipeline rename.json
# 执行
file_organizer apply --plan plan.json

# 自然语言入口
file_organizer ask "重命名为 {date}_{index:03d}{suffix}" --path <path> --yes
```

## 结果格式

`plan.json`（op=rename 的 actions）+ apply 结果 JSON。

## 示例

### 示例 1
- 用户：「重命名为 `{date}_{index:03d}{suffix}`」
- 结果：`IMG_0001.jpg → 2026-09-08_001.jpg`、`IMG_0002.jpg → 2026-09-08_002.jpg`。

### 示例 2
- 用户：「给 PDF 加日期前缀」
- 管道：`rename(template="{date}_{stem}{suffix}", where=extension==pdf)`
- 结果：仅 `.pdf` 文件被加日期前缀，其余文件不变。
