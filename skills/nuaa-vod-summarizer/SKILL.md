---
name: nuaa-vod-summarizer
description: Extract NUAA Feitian Cloud Classroom VOD replay metadata, lesson lists, subtitles, playback URLs, and courseware artifacts from ft.nuaa.edu.cn video-detail pages using a browser login session.
---

# NUAA VOD Summarizer

Use this skill for NUAA Feitian Cloud Classroom pages. Both URL formats are supported:

```text
https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=118467
https://ft.nuaa.edu.cn/jy-application-resourcemanage-ui/#/play-center?teclId=118690
```

The API base (`/jy-application-vod-he` or `/jy-application-resourcemanage`) is auto-detected from the URL.

Assume commands run from this skill root. Otherwise use the absolute path to `scripts/`.

## Core Boundary

- Let scripts handle browser login reuse, API discovery, replay metadata extraction, subtitle export, and artifact writes.
- Let the agent handle transcript diagnosis, terminology correction, semantic reconstruction, and final Markdown prose.
- Deterministic seed notes must not masquerade as finished course notes.
- Do not call a note final when subtitles/transcripts are missing, empty, or obviously partial.

## Main Commands

### Probe one lesson (quick test)

```powershell
python scripts\extract_nuaa_vod.py "<video-detail-url>" --output-dir "<output-dir>" --browser-runtime-auth --manual-wait-seconds 60
```

### Extract ALL transferable lessons (batch)

```powershell
python scripts\extract_nuaa_vod.py "<video-detail-url>" --output-dir "<output-dir>" --browser-runtime-auth --manual-wait-seconds 60 --batch --skip-existing
```

### Extract a specific lesson by ID

```powershell
python scripts\extract_nuaa_vod.py "<video-detail-url>" --output-dir "<output-dir>" --subtitle-course-id 1547370 --manual-wait-seconds 10
```

## Output Structure

```
<output-dir>/
  course.json                          # course-level metadata
  replay_inventory.json                # full lesson list with transfer flags
  raw/
    page.json                          # parsed URL info
    captured_responses.json            # all captured API responses
    storage_state.json                 # browser storage state
    responses/                         # individual response files
  lessons/
    <lesson_id>/
      metadata.json                    # lesson metadata
      raw/
        subtitle.json                  # raw subtitle API response
        transcript.txt                 # cleaned transcript with timestamps
      semantic_rebuild/
        semantic_rebuild_input.json    # packet for semantic rebuild
        semantic_rebuild_prompt.md     # prompt template
      note.md                          # generated Markdown note (after rebuild)
```

## Supported Platforms

Two UI/API pairs are supported, auto-detected from the URL:

| UI host | API base | Main route |
| --- | --- | --- |
| `ft.nuaa.edu.cn/jy-application-vod-he-ui` | `/jy-application-vod-he` | `#/video-detail?id=<teclId>` |
| `ft.nuaa.edu.cn/jy-application-resourcemanage-ui` | `/jy-application-resourcemanage` | `#/play-center?teclId=<teclId>` |

Known API families (both platforms share similar paths under their API base):

- `/v1/subject_vod_list` — lesson list (vod-he)
- `/v1/group_subject_vod_list` — lesson list (resourcemanage)
- `/v1/course_vod_videoinfos` — lesson video metadata
- `/v1/course_vod_urls` — playback URLs
- `/v1/course_vod_subtitle` — AI subtitles (requires `courTransferFlag=true`)
- `/v1/courseware/upload/list` — courseware list
- `/v1/courseware/downLoad` — courseware download
- `/v1/course/verify` — course access check

## Workflow

1. Open the supplied URL (`video-detail` or `play-center`) in a persistent Chromium context.
2. If needed, complete NUAA login in the browser window.
3. Capture NUAA VOD API responses while the page loads.
4. Auto-detect API base from URL markers.
5. Enumerate lessons and identify which have subtitles (`courTransferFlag`).
6. For each target lesson, fetch `<api_base>/v1/course_vod_subtitle`.
7. Save subtitle JSON and cleaned transcript per lesson.
8. Prepare `semantic_rebuild/` packet only when transcript material exists.
9. Generate Markdown notes from transcripts via semantic rebuild.

## Required Replay Diagnosis

Before building any note, classify each lesson into exactly one of:

1. **`waiting_transcript`** — subtitles not yet available (no `courTransferFlag`, or fetch returned empty)
2. **`partial_transcript`** — subtitle exists but is clearly incomplete, garbled beyond repair, or covers only a fraction of the lesson
3. **`transcript_only`** — has complete transcript but no note written yet

Downstream note logic must consume this classification instead of recomputing route decisions.

## Semantic Rebuild Rules

- Perform course-alignment check before treating a note as final.
- Correct obvious ASR term errors when course context makes the intended term clear.
- Keep the lesson time axis visible. Every major section should reference a time range or coarse `MM:SS-MM:SS` marker.
- Keep math as `$...$` or `$$...$$` only (do not wrap formulas in backticks).
- Treat the course transcript as the only primary source for section boundaries, lesson mainline, and completion checks.
- Only mark a lesson final when transcript coverage and summary coverage both pass.
- Reconstruct course-specific substance. Do not substitute generic learning advice for missing semantic understanding.
- If `transcript.txt` is missing, empty, or near-empty, treat the replay as waiting for transcript material. Do not create a formal note from metadata, schedule, title, or courseware alone.

## Authoring Contract

When writing the final student-facing Markdown note:

- You are writing the **finished note**, not a seed note, diagnostic note, or instruction to a future organizer.
- **Read the full transcript.txt** before writing. Use `semantic_rebuild_input.json` only as metadata, time anchors, and artifact index.
- **Do not expose** evidence snippets, candidate phrases, OCR fragments, raw ASR lines, or internal workflow notes.
- Every major time block should explain what **teaching move** happened: definition, model, argument, proof, example, comparison, case discussion, policy explanation, teacher comment, assignment, exam arrangement, or class logistics.
- **Capture high-value classroom signals:** exams, homework, deadlines, submission format, grading weight, reading requirements, teacher-emphasized key points, repeatedly stressed phrases, formulas, theorems, definitions, examples, and common mistakes.
- If the teacher explicitly says something is important, likely to be tested, easy to confuse, often wrong, or needs review after class — **preserve it** in the note.
- If transcript evidence is weak, write the item under **"待核对"** instead of turning it into a confident conclusion.
- The final note must **face the student reader directly**. Avoid phrases like "整理时应...", "后续重写...", "这一段主要在...", or other process commentary.

## Final Note Quality Gate

A user-facing final note must be a **semantic reconstruction**, not a decorated transcript segment list. Before accepting as final, reject if it contains:

- Raw ASR/OCR snippets presented as "代表性表达" or representative expressions
- Headings like "课堂讲解与主题推进 1"
- Boilerplate like "整理时建议不要把这一段只当作..."
- Repeated generic advice across sections instead of course-specific content
- Transcript noise (misrecognized symbols) copied without correction
- Low-quality diagnostics marked as formal notes

If a note fails this gate, keep only extraction artifacts and semantic packet, then mark the lesson as needing semantic rebuild. Do not call it final.

## Course-Domain Reconstruction Guidance

- **Math and statistics:** reconstruct objects, definitions, assumptions, equations, theorems, proof ideas, examples, counterexamples, symbol meanings, and links between results.
- **Engineering and computer science:** reconstruct system components, algorithms, design constraints, implementation steps, experiment setup, failure cases, trade-offs, and how formulas/code relate to the design.
- **Humanities and social sciences:** reconstruct concepts, arguments, historical/institutional background, author positions, evidence, comparisons, cases, and the teacher's evaluative emphasis.
- **Ideological and political courses:** reconstruct policy concepts, theoretical claims, historical context, named documents/events, value judgments, exam-oriented formulations, and examples used to explain abstract claims.
- **Language, writing, and communication courses:** reconstruct vocabulary, rhetorical patterns, text structure, examples, correction points, practice requirements, and teacher feedback.
- **Lab, design, or project courses:** reconstruct task goals, deliverables, tools, operation steps, data requirements, safety/format constraints, grading criteria, and troubleshooting advice.

## Transcript-Only Rule

When a lesson is classified as `transcript_only`:

- Do NOT emit fake content templates (e.g., "课程定位 / 基础概念 / 方法流程").
- Let scripts provide only time segments from the transcript, representative transcript lines, and transcript overview.
- Let the agent infer the real lesson structure from the transcript plus course context.
- Do not ask scripts to pre-confirm concepts from transcript-only material.

## PPT / Courseware Rule

- Prefer teacher audio/subtitle stream by default.
- Treat PPT and courseware as **auxiliary only**, even when available.
- PPT may help with term spelling, page/book titles, formula symbols, and logistics screenshots.
- PPT **must not** decide section boundaries, lesson mainline, concept generation, or completion state.

## Failure Rules

- If authentication fails or no VOD API responses are captured, keep `raw/page.json` and explain that a logged-in browser session is required.
- If subtitle data is absent for a lesson, mark it as no-subtitle and skip.
- If subtitle text is empty or near-empty, do not produce a final note.
- If transcript coverage is clearly partial, keep only a diagnostic draft rather than a final note.
- Treat courseware/PPT as auxiliary only; it must not replace transcript evidence.
- If session reuse fails, rerun with `--browser-runtime-auth`.

On Windows, prefer PowerShell commands. For inline Python, use:

```powershell
@'
print("hello")
'@ | python -
```
