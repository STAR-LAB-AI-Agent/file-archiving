# Pipeline DSL reference

A **pipeline** is a JSON document describing a sequence of organizing stages. The CLI
runs the stages in order over one in-memory list of file records and then turns the
result into a plan.

```json
{
  "stages": [
    {"op": "classify", "by": "type"},
    {"op": "move", "rule": "by_category"}
  ]
}
```

Save it as a `.json` file and pass it with `--pipeline <file>` to `plan` or `organize`.

## Stages

| `op` | Purpose | Key parameters |
|---|---|---|
| `filter` | keep only the records matching a condition | `where` |
| `classify` | write a category onto each record | `by` = `type` \| `name` \| `content`; `mode` = `overwrite` \| `append` |
| `sort` | reorder records (affects later `rename` indexes) | `by` = `name` \| `size` \| `mtime` \| `type` \| `category`; `order` = `asc` \| `desc` |
| `rename` | compute a new file name | `template`; `where`; `index_start` |
| `move` | compute a target directory | `rule` = `by_category` \| `to_path`; `target`; `preserve` |
| `tag` | attach tags | `tags`; `where` |
| `dedup` | group duplicates by content hash | `by` = `content_hash`; `keep` |

### classify

- `by=type` maps the extension to a category folder: `文档 / 表格 / 演示 / 图片 /
  压缩包 / 音频 / 视频 / 程序`, else `其他`.
- `by=name` matches file-name keywords.
- `by=content` extracts text (first ~512 chars) and matches content keywords.
- `mode=append` appends to the existing category instead of overwriting it, producing
  two-level categories such as `马克思主义/文档`.

### move

- `rule=by_category` → `<root>/<category>` (flattens nested folders).
- `rule=by_category` + `preserve: true` → `<file's own folder>/<category>` (keeps the
  existing tree; already-placed files are skipped, so it is idempotent).
- `rule=to_path` + `target` → the given folder. A **relative** target resolves under
  the root; an **absolute** target may point outside the root (explicit cross-root move).

### dedup

`dedup` only **marks** duplicates (it writes `is_kept` / `dup_group`); it does **not**
move anything. To separate the duplicates, follow it with a `filter` and a `move`:

```json
{"stages": [
  {"op": "dedup", "by": "content_hash", "keep": "oldest"},
  {"op": "filter", "where": {"field": "is_kept", "op": "eq", "value": false}},
  {"op": "move", "rule": "to_path", "target": "重复文件"}
]}
```

## `where` conditions

```text
where := {"field","op","value"} | {"and":[where...]} | {"or":[where...]} | {"not": where}
field ∈ {name, stem, suffix, extension, mime_type, size, mtime, mtime_days, category, tags}
op    ∈ {eq, ne, in, not_in, gt, gte, lt, lte, contains, startswith, endswith, regex}
```

Example — PDF or DOCX larger than 10 MB:

```json
{"and": [
  {"or": [
    {"field": "extension", "op": "eq", "value": "pdf"},
    {"field": "extension", "op": "eq", "value": "docx"}
  ]},
  {"field": "size", "op": "gt", "value": 10485760}
]}
```

## Rename templates

| Placeholder | Meaning | Example |
|---|---|---|
| `{date}` | modification date | `2026-09-08` |
| `{time}` | modification time | `124059` |
| `{stem}` | file name without extension | `report` |
| `{name}` | full file name | `report.pdf` |
| `{suffix}` | extension **with** dot | `.pdf` |
| `{ext}` | extension **without** dot | `pdf` |
| `{category}` | current category | `文档` |
| `{index}` | running index, `{index:03d}` → `001` | `001` |

Use `{suffix}` (not `{ext}`) when you want `name_001.jpg`; `{ext}` alone would produce
`name_001jpg`.

## Order matters

`sort` must come **before** `rename` for the index to follow the sorted order:

```json
{"stages": [
  {"op": "classify", "by": "type"},
  {"op": "sort", "by": "mtime", "order": "asc"},
  {"op": "rename", "template": "{date}_{index:03d}{suffix}",
   "where": {"field": "category", "op": "endswith", "value": "图片"}},
  {"op": "move", "rule": "by_category"}
]}
```

`filter` **removes** non-matching records permanently. To restrict a single step while
keeping the other files, use that step's own `where` instead of a separate `filter`.

## Composite example — content, then format, then rename images

```json
{"stages": [
  {"op": "classify", "by": "content"},
  {"op": "classify", "by": "type", "mode": "append"},
  {"op": "sort", "by": "mtime", "order": "asc"},
  {"op": "rename", "template": "{date}_{index:03d}{suffix}",
   "where": {"field": "category", "op": "endswith", "value": "图片"}},
  {"op": "move", "rule": "by_category"}
]}
```
