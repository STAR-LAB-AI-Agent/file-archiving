---
name: ai-file-organizer
description: >-
  Organize files on the local disk: scan a folder, classify files by type, name or
  content, batch-rename, move or archive them, and find duplicates. Use this whenever
  the user asks to tidy up, sort, categorize, rename, archive, or de-duplicate files
  in a directory, or to keep a folder organized automatically. Always preview the plan
  and get confirmation before applying changes, and roll back with the undo command.
metadata:
  nanobot:
    requires:
      bins:
        - file_organizer
---

# AI File Organizer

`file_organizer` is a local command-line tool that organizes files inside a directory.
Scanning, classifying, renaming, moving and de-duplicating all run **locally and
deterministically** — the model decides *what* to do, the CLI does the work.

## When to use this skill

Use it when the user wants to:

- tidy up / sort / categorize a folder (e.g. a Downloads folder)
- batch-rename files (by date, index, or existing metadata)
- move or archive files by condition (extension, size, age)
- find and separate duplicate files
- keep watching a folder and organize newly added files

## Golden rule: preview, confirm, then apply

**Never change files without showing the plan first.**

1. Build a plan and show it to the user (`--dry-run` or `plan`).
2. Ask the user to confirm.
3. Apply only after confirmation (`--yes` or `apply`).
4. If the result is wrong, roll back with `undo`.

## Commands

| Command | Purpose |
|---|---|
| `file_organizer scan --path <dir> --table` | list files + metadata (read-only) |
| `file_organizer plan --path <dir>` | build and print a plan (writes nothing) |
| `file_organizer organize --path <dir> --dry-run` | full default pipeline, preview only |
| `file_organizer organize --path <dir> --yes` | full default pipeline, apply |
| `file_organizer apply --plan plan.json` | apply a previously saved plan |
| `file_organizer undo --path <dir> [--n 2]` | roll back the last N organizes |
| `file_organizer ask "<instruction>" --path <dir>` | natural-language entry |

Add `--preserve-structure` to `organize` / `ask` / `plan` when the folder already has
sub-folders that should stay nested (the default flattens everything into category
folders at the root).

## Typical workflows

### 1. Tidy a folder by file type

```bash
file_organizer organize --path "C:/Users/me/Downloads" --dry-run
# show the preview, ask the user to confirm
file_organizer organize --path "C:/Users/me/Downloads" --yes
```

### 2. Rename photos by capture date

```bash
file_organizer ask "重命名为 {date}_{index:03d}{suffix}" --path "C:/photos" --dry-run
file_organizer ask "重命名为 {date}_{index:03d}{suffix}" --path "C:/photos" --yes
```

### 3. Archive old PDFs into a sub-folder

Create a pipeline file and run it:

```json
{"stages": [
  {"op": "filter", "where": {"and": [
    {"field": "extension", "op": "eq", "value": "pdf"},
    {"field": "mtime_days", "op": "gt", "value": 90}
  ]}},
  {"op": "move", "rule": "to_path", "target": "归档"}
]}
```

```bash
file_organizer plan   --path "C:/docs" --pipeline archive.json
file_organizer apply  --plan plan.json
```

### 4. Extract every .docx into a sibling folder

```json
{"stages": [
  {"op": "filter", "where": {"field": "extension", "op": "eq", "value": "docx"}},
  {"op": "move", "rule": "to_path", "target": "C:/target/docs"}
]}
```

`to_path` with an **absolute** path is allowed to cross the root directory.

### 5. Roll back

```bash
file_organizer undo --path "C:/Users/me/Downloads"
```

## Composite requests → pipeline

For requests that chain several steps ("classify by content, then by format; rename
images by time"), write a **pipeline JSON** and pass it with `--pipeline`. The full DSL
(stages, `where` conditions, rename templates) is in `references/pipeline.md` — read it
before writing a non-trivial pipeline.

## Content-based classification (you must supply the keywords)

`classify(by=content)` extracts the first ~512 characters of each file and matches them
against keyword rules. **The tool ships with NO built-in content rules** — a hardcoded
rule set matches unrelated documents and yields wrong categories. So `classify(by=content)`
fails fast when no rules are supplied; do not expect it to "just work".

When the user asks to classify by content, obtain the keywords first, in one of two ways.

**Option A — you extract them yourself (recommended; you can read the folder):**

1. List the files and read a representative sample (use the built-in `read` / `grep`
   tools, or `file_organizer scan --path <dir> --table`).
2. Pick 3–8 themes and, for each, 3–8 keywords that **actually occur** in those
   documents. Choose discriminating terms — avoid generic words that appear everywhere.
3. Write them to a rules file:

   ```json
   {"content_rules": {
     "马克思主义": ["马克思", "资本论", "剩余价值", "阶级斗争"],
     "调查报告":   ["调查", "报告", "工人", "工资"]
   }}
   ```

4. Pass it in with `--rules rules.json` (or inline under the pipeline's `rules` key).

**Option B — let the tool call a model to do the extraction** (needs `MODEL_API_KEY`):

```bash
file_organizer discover-rules --path "C:/docs" --output rules.json
```

Then run the pipeline with those rules:

```bash
file_organizer organize --path "C:/docs" --pipeline p.json --rules rules.json
```

## Safety

- The tool refuses to operate on OS system directories.
- Move targets must stay inside the given root, except explicit absolute `to_path`.
- Name conflicts default to `skip`; use `--conflict rename_suffix` to keep every file.
- Every `apply` writes an undo record, so any change can be reversed.

## Watching a folder (separate script, not this skill)

`watch-agent` is a **separate long-running script** shipped with the same project, not a
skill. It watches a folder recursively, calls a model when something changes, and applies
the returned pipeline. Start it only if the user explicitly asks for automatic
organization:

```bash
watch-agent --path "C:/inbox" --debounce 5
```
