---
name: obsidian-course-vault
description: Build and maintain a semester-long Obsidian course vault from NUAA VOD extraction output. Creates course overviews, lesson notes, concept pages, and sync trackers.
---

# Obsidian Course Vault (NUAA)

Use this skill to build a long-term Obsidian course knowledge base from NUAA VOD extractions.

Assume commands run from this skill root.

## Core Boundary

- Scripts handle vault structure, file writes, index maintenance, and replay-to-vault bridging.
- The agent handles note writing, concept extraction, affairs review, and graph curation.
- A lesson without a finished `note.md` stays in `待整理回放.md`, not in `已整理课次.md`.

## Main Commands

**Initialize a new vault**:

```powershell
python scripts\init_obsidian_course_vault.py --vault-dir "<vault-dir>"
```

**Add a course**:

```powershell
python scripts\add_course.py --vault-dir "<vault-dir>" --course-name "<课程名>"
```

**Sync NUAA VOD extraction into the vault**:

```powershell
python scripts\sync_nuaa_course.py --vault-dir "<vault-dir>" --course-name "<课程名>" --vod-output-dir "<vod-output-dir>"
```

The sync script reads `course.json`, `replay_inventory.json`, and each lesson's `note.md` from the VOD output, then refreshes course trackers and copies finished notes into the vault.

## Workflow

### 1. Initialize the vault (once)

```powershell
python scripts\init_obsidian_course_vault.py --vault-dir "D:\Obsidian\NUAA-Courses"
```

Creates the standard Obsidian vault structure with templates and admin pages.

### 2. Add a course

```powershell
python scripts\add_course.py --vault-dir "D:\Obsidian\NUAA-Courses" --course-name "操作系统"
```

### 3. Extract and write notes

Use `nuaa-vod-summarizer` to extract lessons, then write `note.md` for each finished lesson.

### 4. Sync into the vault

```powershell
python scripts\sync_nuaa_course.py --vault-dir "D:\Obsidian\NUAA-Courses" --course-name "操作系统" --vod-output-dir "..\nuaa-vod-summarizer\work\118467"
```

This updates:
- `00-课程总览.md` — course metadata and lesson index
- `已整理课次.md` — table of finished lessons with concept counts
- `待整理回放.md` — list of lessons still pending notes
- `事务.md` — aggregated homework/exam/notice entries from finished notes
- Lesson note files — copied into `01-Courses/<课程名>/课次/`

## Vault Structure

```
vault/
  00-Home.md
  01-Courses/
    <课程名>/
      00-课程总览.md
      事务.md
      已整理课次.md
      待整理回放.md
      回放同步.md
      章节完成度.md
      待回看问题.md
      课次/
        2026-03-09 操作系统 第2节.md
        ...
  02-Concepts/
    <课程名>/
      <课程名>概念图谱.md
  03-Admin/
    作业总表.md
    考试与通知.md
  04-Templates/
  05-Inbox/
```

## Failure Rules

- Never create a vault inside `nuaa-vod-summarizer/work/` — vaults are long-lived, work dirs are ephemeral.
- If `note.md` doesn't exist for a lesson, mark it in `待整理回放` rather than inventing content.
- Do not overwrite an existing `note.md` during sync unless `--force` is passed.
- Course affairs in `事务.md` must come from actual note content, not from transcript keyword extraction.

## Integration with nuaa-vod-summarizer

The bridge is the `course.json` + `replay_inventory.json` + per-lesson `note.md`:

```
vod-output-dir/
  course.json              ← course identity
  replay_inventory.json    ← full lesson list
  lessons/<id>/
    metadata.json          ← lesson metadata
    note.md                ← finished Markdown note (the source of truth)
```

Only lessons with `note.md` present and non-empty are treated as "finished" and synced into the vault.
