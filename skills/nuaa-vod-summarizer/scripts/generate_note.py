from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_note_context(lesson_dir: Path) -> str:
    """Assemble the full context needed to generate a Markdown note."""
    metadata = load_json(lesson_dir / "metadata.json")
    transcript_path = lesson_dir / "raw" / "transcript.txt"
    semantic_path = lesson_dir / "semantic_rebuild" / "semantic_rebuild_input.json"

    transcript = ""
    if transcript_path.exists():
        transcript = transcript_path.read_text(encoding="utf-8")

    parts: list[str] = []

    # Metadata block
    parts.append("## Lesson Metadata\n")
    parts.append(f"- **课程**: {metadata.get('subjName', '')}")
    parts.append(f"- **教师**: {', '.join(metadata.get('teacNames', []))}")
    parts.append(f"- **时间**: {metadata.get('courBeginTime', '')} - {metadata.get('courEndTime', '')}")
    parts.append(f"- **节次**: 第{metadata.get('letiNumber', '')}节")
    parts.append(f"- **周次**: 第{metadata.get('zc', '')}周")
    parts.append(f"- **教室**: {metadata.get('clroName', '')}")
    parts.append(f"- **课程序号**: {metadata.get('teclCode', '')}\n")

    if semantic_path.exists():
        si = load_json(semantic_path)
        parts.append("## Semantic Rebuild Input\n")
        parts.append(f"- Source: {si.get('source', '')}")
        parts.append(f"- Lesson ID: {si.get('lesson_id', '')}")
        if si.get("notes"):
            parts.append(f"- Notes: {'; '.join(si['notes'])}\n")

    parts.append("## Transcript\n")
    parts.append(transcript)
    parts.append("")

    return "\n".join(parts)


NOTE_PROMPT = """## Task

Generate a student-facing Markdown course note from the transcript above.

## Note Structure

Use this exact structure:

```markdown
# {课程名} — 第{节次}节 ({日期})

**教师**: {教师} | **教室**: {教室} | **周次**: 第{周次}周

---

## 本节主线

{2-4 句话概括本节课的核心内容和逻辑脉络}

---

## 时间轴

{以 5-10 分钟为颗粒度，列出关键话题转换}

| 时间 | 话题 |
|------|------|
| 00:00 | ... |
| ... | ... |

---

## 关键概念

{列出本节课引入或深入讲解的重要概念，每个概念给一句话解释}

- **概念A**: ...
- **概念B**: ...

---

## 要点详述

{按主题分段展开，保留老师讲解的逻辑层次。不是逐字记录，而是理解后重述}

### 主题1

...

### 主题2

...

---

## 作业 / 考试 / 通知

{从字幕中提取明确提到的作业、考试安排、通知事项。无法确认的不写}

- ...

---

## 待核对

{字幕不清晰、不确定正确性的内容放这里}

- ...

---

## 回看建议

{如果有没讲完、需要复习、或重点回看的段落，标注时间戳}

- ...
```

## Rules

1. **Never invent content.** Every claim must be traceable to the transcript.
2. **Rephrase in your own words.** Do not copy ASR output verbatim as final prose.
3. **Flag ASR noise.** If a sentence is garbled, mark it under "待核对" rather than guessing.
4. **Keep student-facing.** Don't expose API fields, internal paths, or workflow details.
5. **Homework/exam info only when explicit.** "下节课交" with a clear topic counts; vague "回去看看" does not.
6. **Use timestamps** from the transcript `[MM:SS-MM:SS]` format when referencing specific moments.
7. **Write in Chinese** with technical terms in English where appropriate (e.g., PCB, PID, fork).

---

Generate the note now based on the lesson context above.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare context for NUAA lesson note generation.")
    parser.add_argument("lesson_dir", help="Path to a lesson directory (e.g., work/118467/lessons/1547370)")
    parser.add_argument("--print-context", action="store_true", help="Print full context for the agent.")
    parser.add_argument("--print-prompt", action="store_true", help="Print the note generation prompt template.")
    args = parser.parse_args()

    lesson_dir = Path(args.lesson_dir).resolve()
    if not lesson_dir.is_dir():
        print(f"Not a directory: {lesson_dir}", file=__import__("sys").stderr)
        return 1

    if args.print_prompt:
        print(NOTE_PROMPT)
        return 0

    if args.print_context:
        print(build_note_context(lesson_dir))
        return 0

    # Default: print context then prompt
    print(build_note_context(lesson_dir))
    print("\n---\n")
    print(NOTE_PROMPT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
