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
- Deterministic seed notes must not masquerade as finished course notes.
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

## Required Replay Diagnosis

Before syncing any lesson note, classify each lesson into exactly one of:

1. **`waiting_transcript`** — subtitles not yet available
2. **`partial_transcript`** — subtitle exists but incomplete or garbled
3. **`transcript_only`** — has transcript but no note yet

This classification is produced by `nuaa-vod-summarizer`. Downstream vault sync must consume this classification — do not copy placeholder or diagnostic notes into the vault as finished content.

## Course Affairs Workflow

Course affairs (homework, exams, scheduling) follow a careful pipeline:

1. Finished notes write affairs under `## 课程事务` with categories: homework, exams, course arrangements, notices.
2. `sync_nuaa_course.py` extracts affairs from finished notes and writes candidates.
3. Agent review condenses candidates into `事务.md` and Admin tables.
4. Only transcript-supported affairs as confident bullets; uncertain items go under "待核对".

Do NOT roll up affairs from:
- Lessons with `waiting_transcript`
- Lessons with `partial_transcript`
- Notes still pending semantic rebuild
- Draft notes not yet validated

Affairs review must explicitly reject: ordinary teaching content, general encouragement, repeated mentions of the same item, vague notes without deliverables, and keyword hits that do not indicate actual affairs.

## Authoring Contract

When writing notes for vault integration, follow the same authoring contract as `nuaa-vod-summarizer`:

- Face the student reader directly. No process commentary.
- Read full transcript before writing.
- Every major time block explains the teaching move.
- Capture exams, deadlines, stressed points, formulas, definitions, common mistakes.
- Weak evidence goes under "待核对".
- Do not expose ASR fragments, OCR snippets, or workflow notes.

## Final Note Quality Gate

A lesson is not finished if it contains:

- Raw ASR/OCR snippets
- Generic headings like "课堂讲解与主题推进 1"
- Repeated generic advice across sections
- Misrecognized math symbols copied without correction
- Diagnostic markers treated as formal notes

For math-heavy courses, the note must reconstruct concrete mathematical objects, equations, proofs, and examples, or remain a draft.

## Course-Domain Reconstruction Guidance

- **Math and statistics:** reconstruct objects, definitions, assumptions, equations, theorems, proof ideas, examples, counterexamples, symbol meanings.
- **Engineering and computer science:** reconstruct system components, algorithms, design constraints, implementation steps, trade-offs.
- **Humanities and social sciences:** reconstruct concepts, arguments, background, author positions, evidence, comparisons.
- **Ideological and political courses:** reconstruct policy concepts, theoretical claims, historical context, named documents/events, exam-oriented formulations.
- **Language, writing, and communication courses:** reconstruct vocabulary, rhetorical patterns, text structure, examples, correction points.
- **Lab, design, or project courses:** reconstruct task goals, deliverables, tools, operation steps, grading criteria.

## Output Rules

- Public outputs are ONLY finished products. Internal artifacts stay out of the vault.
- Never link internal artifacts from public outputs.
- User-facing placeholder text must avoid process language like "agent review" or "semantic rebuild".
- Keep concept links in note body, not just frontmatter.
- Keep visible time references in `HH:MM:SS` format.
- Math stays in `$...$` or `$$...$$`.
- Do not create concept pages from low-quality snippets.
- Do not add rejected or draft notes to trackers or graph growth.

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

## Course Identity Rule

Course title — not `course_id`, lecturer, schedule, or classroom — determines identity. Multiple source URLs can feed the same titled course as long as provenance is preserved in sync metadata.

## Failure Rules

- Never create a vault inside `nuaa-vod-summarizer/work/` — vaults are long-lived, work dirs are ephemeral.
- If `note.md` doesn't exist for a lesson, mark it in `待整理回放` rather than inventing content.
- Do not overwrite an existing `note.md` during sync unless `--force` is passed.
- Course affairs in `事务.md` must come from actual note content, not from transcript keyword extraction.
- Empty or near-empty transcripts count as `waiting_transcript` — do not build placeholder notes.
- Partial transcripts get only diagnostic drafts, not final notes.

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
