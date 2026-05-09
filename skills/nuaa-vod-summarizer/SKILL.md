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

## Failure Rules

- If authentication fails or no VOD API responses are captured, keep `raw/page.json` and explain that a logged-in browser session is required.
- If subtitle data is absent for a lesson, mark it as no-subtitle and skip.
- If subtitle text is empty or near-empty, do not produce a final note.
- Treat courseware/PPT as auxiliary only; it must not replace transcript evidence.

On Windows, prefer PowerShell commands. For inline Python, use:

```powershell
@'
print("hello")
'@ | python -
```
