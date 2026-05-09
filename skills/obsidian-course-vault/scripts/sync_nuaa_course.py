#!/usr/bin/env python3
"""Sync NUAA VOD extraction output into an Obsidian course vault."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\\\|?*]+', "_", value.strip())


def extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML-like frontmatter from a markdown note."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm: dict[str, Any] = {}
    for line in parts[1].strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
            fm[key] = val
    return fm, parts[2]


def extract_affairs_from_note(note_text: str) -> dict[str, list[str]]:
    """Extract 课程事务 entries from a note."""
    affairs: dict[str, list[str]] = {"作业": [], "考试": [], "通知": [], "课程安排": []}
    _, body = extract_frontmatter(note_text)

    in_affairs = False
    current_category: str | None = None
    for line in body.split("\n"):
        if re.match(r"^##\s+课程事务|^##\s+课堂事务", line):
            in_affairs = True
            continue
        if in_affairs and re.match(r"^##\s+", line):
            in_affairs = False
            current_category = None
            continue
        if not in_affairs:
            continue
        m = re.match(r"^###\s+(.+)", line)
        if m:
            current_category = m.group(1).strip()
            continue
        if current_category and line.strip().startswith("- ") and len(line.strip()) > 2:
            entry = line.strip()[2:].strip()
            if entry and entry not in ("-", "当前没有明确", "还没有汇总"):
                if current_category in affairs:
                    affairs[current_category].append(entry)
    return affairs


def collect_lesson_notes(vod_dir: Path) -> list[dict[str, Any]]:
    """Walk the lessons directory and collect all finished notes."""
    lessons_dir = vod_dir / "lessons"
    if not lessons_dir.is_dir():
        return []

    notes: list[dict[str, Any]] = []
    for lesson_dir in sorted(lessons_dir.iterdir()):
        if not lesson_dir.is_dir():
            continue
        note_path = lesson_dir / "note.md"
        metadata_path = lesson_dir / "metadata.json"
        if not note_path.exists() or not metadata_path.exists():
            continue
        note_text = note_path.read_text(encoding="utf-8").strip()
        if not note_text:
            continue
        metadata = load_json(metadata_path)
        begin_time = metadata.get("courBeginTime", "")
        notes.append({
            "lesson_id": lesson_dir.name,
            "date": begin_time[:10] if begin_time else "",
            "begin_time": begin_time,
            "leti_number": metadata.get("letiNumber", ""),
            "subj_name": metadata.get("subjName", ""),
            "teac_names": metadata.get("teacNames", []),
            "clro_name": metadata.get("clroName", ""),
            "zc": metadata.get("zc", ""),
            "title": f"{begin_time[:10]} {metadata.get('subjName', '')} 第{metadata.get('letiNumber', '')}节",
            "note_text": note_text,
            "note_path": note_path,
        })
    return notes


def collect_backlog_lessons(vod_dir: Path, finished_ids: set[str]) -> list[dict[str, Any]]:
    """Collect lessons that don't have a finished note yet."""
    inventory_path = vod_dir / "replay_inventory.json"
    if not inventory_path.exists():
        return []

    inventory = load_json(inventory_path)
    lessons = inventory.get("lessons", [])
    backlog: list[dict[str, Any]] = []
    for lesson in lessons:
        lid = str(lesson.get("id", ""))
        if lid in finished_ids:
            continue
        if not lesson.get("courTransferFlag"):
            continue  # skip lessons without transcript
        begin = lesson.get("courBeginTime", "")
        backlog.append({
            "lesson_id": lid,
            "date": begin[:10] if begin else "",
            "leti_number": lesson.get("letiNumber", ""),
            "subj_name": lesson.get("subjName", ""),
            "begin_time": begin,
            "zc": lesson.get("zc", ""),
        })
    return sorted(backlog, key=lambda x: x.get("begin_time", ""))


def write_course_overview(course_dir: Path, course_info: dict[str, Any], notes: list[dict[str, Any]]) -> None:
    """Regenerate 00-课程总览.md."""
    name = course_info.get("subjName", "")
    teachers = ", ".join(course_info.get("teacNames", []))
    tecl_code = course_info.get("teclCode", "")
    total = course_info.get("total_lessons", 0)
    transferable = course_info.get("transferable_lessons", 0)
    date_range = course_info.get("date_range", {})
    first_date = (date_range.get("first") or "")[:10]
    last_date = (date_range.get("last") or "")[:10]

    lines = [
        "---",
        f"course: {name}",
        f"teacher: {teachers}",
        f"tecl_code: {tecl_code}",
        f"date_range: {first_date} ~ {last_date}",
        "---",
        "",
        f"# {name}",
        "",
        "## 课程信息",
        "",
        f"- 教师：{teachers}",
        f"- 课程序号：{tecl_code}",
        f"- 时间范围：{first_date} ~ {last_date}",
        f"- 课次总数：{total}（有 AI 字幕：{transferable}）",
        "",
        "## 章节地图",
        "",
        f"- 图谱入口：[[../../02-Concepts/{name}/{name}概念图谱]]",
        "- 第一部分：",
        "- 第二部分：",
        "- 第三部分：",
        "",
        "## 课次索引",
        "",
    ]

    if notes:
        for n in sorted(notes, key=lambda x: x.get("begin_time", "")):
            note_filename = sanitize_filename(n["title"])
            lines.append(f"- [[课次/{note_filename}|{n['title']}]]")
    else:
        lines.append("- （暂无已完成笔记）")

    lines.extend([
        "",
        "## 课程事务",
        "",
        "- [[事务]]",
        "- [[已整理课次]]",
        "- [[待整理回放]]",
        "- [[待回看问题]]",
        "- [[章节完成度]]",
        "- [[回放同步]]",
        "",
    ])

    (course_dir / "00-课程总览.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_lesson_index(course_dir: Path, notes: list[dict[str, Any]]) -> None:
    """Regenerate 已整理课次.md."""
    lines = [
        "# 已整理课次",
        "",
        "| 日期 | 节次 | 标题 | 周次 | 教室 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for n in sorted(notes, key=lambda x: x.get("begin_time", "")):
        date = n["date"]
        leti = n["leti_number"]
        title = n["title"]
        zc = n.get("zc", "")
        clro = n.get("clro_name", "")
        lines.append(f"| {date} | 第{leti}节 | {title} | 第{zc}周 | {clro} |")

    if not notes:
        lines.append("| - | - | 还没有已整理的课次 | - | - |")

    lines.append("")
    (course_dir / "已整理课次.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_backlog(course_dir: Path, backlog: list[dict[str, Any]]) -> None:
    """Regenerate 待整理回放.md."""
    lines = [
        "# 待整理回放",
        "",
        "以下课次有 AI 字幕但尚未生成笔记：",
        "",
        "| 日期 | 节次 | 课程 | 周次 | 课次ID |",
        "| --- | --- | --- | --- | --- |",
    ]
    for b in backlog:
        date = b["date"]
        leti = b.get("leti_number", "")
        name = b.get("subj_name", "")
        zc = b.get("zc", "")
        lid = b.get("lesson_id", "")
        lines.append(f"| {date} | 第{leti}节 | {name} | 第{zc}周 | {lid} |")

    if not backlog:
        lines.append("| - | - | 所有可转写课次都已整理完毕 | - | - |")

    lines.append("")
    (course_dir / "待整理回放.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_affairs(course_dir: Path, notes: list[dict[str, Any]]) -> None:
    """Regenerate 事务.md from finished note affairs sections."""
    all_affairs: dict[str, set[str]] = {"作业": set(), "考试": set(), "通知": set(), "课程安排": set()}
    for n in notes:
        note_affairs = extract_affairs_from_note(n["note_text"])
        for cat in all_affairs:
            for entry in note_affairs.get(cat, []):
                all_affairs[cat].add(entry)

    lines = ["# 事务", ""]
    for cat, entries in [("作业", all_affairs["作业"]), ("考试", all_affairs["考试"]),
                          ("通知", all_affairs["通知"]), ("课程安排", all_affairs["课程安排"])]:
        lines.append(f"## {cat}")
        lines.append("")
        if entries:
            for entry in sorted(entries):
                lines.append(f"- {entry}")
        else:
            lines.append(f"- 当前没有明确{cat}事务。")
        lines.append("")

    (course_dir / "事务.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sync_note(course_dir: Path, vod_dir: Path, notes: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> None:
    """Regenerate 回放同步.md."""
    lines = [
        "# 回放同步",
        "",
        f"- **来源**：南航飞天云课堂 VOD",
        f"- **VOD 数据目录**：`{vod_dir}`",
        f"- **最后同步**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **已完成笔记**：{len(notes)} 篇",
        f"- **待整理**：{len(backlog)} 节",
        "",
    ]
    (course_dir / "回放同步.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_notes_to_vault(course_dir: Path, notes: list[dict[str, Any]], force: bool) -> int:
    """Copy finished note.md files into the vault 课次 directory."""
    lessons_dir = course_dir / "课次"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for n in notes:
        dest_name = sanitize_filename(n["title"]) + ".md"
        dest = lessons_dir / dest_name
        if dest.exists() and not force:
            continue
        dest.write_text(n["note_text"], encoding="utf-8")
        copied += 1
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync NUAA VOD extraction into an Obsidian vault.")
    parser.add_argument("--vault-dir", required=True, help="Path to the Obsidian vault.")
    parser.add_argument("--course-name", required=True, help="Course name (must match an existing course folder).")
    parser.add_argument("--vod-output-dir", required=True, help="Path to NUAA VOD extraction output directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing note files in vault.")
    args = parser.parse_args()

    vault_dir = Path(args.vault_dir).resolve()
    vod_dir = Path(args.vod_output_dir).resolve()
    course_name = args.course_name

    course_dir = vault_dir / "01-Courses" / course_name
    if not course_dir.is_dir():
        print(f"Course '{course_name}' not found in vault. Run add_course.py first.", file=sys.stderr)
        sys.exit(1)

    course_json = vod_dir / "course.json"
    if not course_json.exists():
        print(f"course.json not found in {vod_dir}. Run nuaa-vod-summarizer first.", file=sys.stderr)
        sys.exit(1)

    course_info = load_json(course_json)
    notes = collect_lesson_notes(vod_dir)
    finished_ids = {n["lesson_id"] for n in notes}
    backlog = collect_backlog_lessons(vod_dir, finished_ids)

    print(f"Course: {course_info.get('subjName', '')}")
    print(f"Finished notes: {len(notes)}")
    print(f"Backlog (pending): {len(backlog)}")

    write_course_overview(course_dir, course_info, notes)
    write_lesson_index(course_dir, notes)
    write_backlog(course_dir, backlog)
    write_affairs(course_dir, notes)
    write_sync_note(course_dir, vod_dir, notes, backlog)

    copied = copy_notes_to_vault(course_dir, notes, args.force)
    print(f"Notes copied to vault: {copied}")

    print(json.dumps({
        "status": "ok",
        "finished": len(notes),
        "backlog": len(backlog),
        "copied": copied,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
