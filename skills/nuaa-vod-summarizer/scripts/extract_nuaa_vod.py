from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from playwright.async_api import BrowserContext, Page, async_playwright

KNOWN_API_MARKERS = (
    "/jy-application-vod-he/",
    "/jy-application-resourcemanage/",
)

INTERESTING_PATHS = (
    "/v1/subject_vod_list",
    "/v1/group_subject_vod_list",
    "/v1/course_vod_videoinfos",
    "/v1/course_vod_urls",
    "/v1/course_vod_subtitle",
    "/v1/courseware/upload/list",
    "/v1/courseware/downLoad",
    "/v1/course/verify",
    "/v1/vod/play/record",
    "/v1/course/status",
    "/v1/vod_live",
    "/v1/myself/curriculum",
    "/v1/resource/downLoad",
    "/v1/list/vod/collection",
)

MOJIBAKE_HINTS = (
    "鎿", "嶴", "綽", "绯", "荻", "粺",
    "浣", "嗘", "槸", "濡", "储", "涉",
)

_api_base: str = "/jy-application-vod-he"


def parse_video_detail_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    fragment = parsed.fragment or ""
    fragment_path, _, fragment_query = fragment.partition("?")
    params = parse_qs(fragment_query)
    tecl_id = (params.get("id") or params.get("teclId") or [None])[-1]
    return {
        "url": url,
        "host": parsed.netloc,
        "route": fragment_path,
        "query": {key: values[-1] for key, values in params.items() if values},
        "tecl_id": tecl_id,
        "course_id": (params.get("courseId") or [None])[-1],
        "api_base": detect_api_base(url),
    }


def normalize_url(url: str) -> str:
    """Convert play-center URL to video-detail URL so the same extraction works."""
    if "play-center" in url and "teclId=" in url:
        tecl_id = (parse_qs(urlparse(url).fragment.partition("?")[2]).get("teclId") or [None])[-1]
        if tecl_id:
            return f"https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id={tecl_id}"
    return url


def is_interesting_url(url: str) -> bool:
    return any(marker.rstrip("/") in url for marker in KNOWN_API_MARKERS) and any(
        path in url for path in INTERESTING_PATHS
    )


def detect_api_base(url: str) -> str:
    """Extract the API base from a URL or default to /jy-application-vod-he/."""
    for marker in KNOWN_API_MARKERS:
        if marker.rstrip("/") in url:
            return marker.rstrip("/")
    return "/jy-application-vod-he"


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w.\-]+", "_", value, flags=re.UNICODE).strip("_")
    return value[:120] or "response"


def json_default(value: Any) -> str:
    return str(value)


def mojibake_score(value: str) -> int:
    return sum(value.count(hint) for hint in MOJIBAKE_HINTS) + value.count("�")


def repair_text(value: str) -> str:
    if not value:
        return value
    try:
        repaired = value.encode("gbk").decode("utf-8")
    except Exception:
        return value
    if mojibake_score(repaired) < mojibake_score(value) or any(
        hint in value for hint in MOJIBAKE_HINTS
    ):
        return repaired
    return value


def repair_json_text(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: repair_json_text(value) for key, value in data.items()}
    if isinstance(data, list):
        return [repair_json_text(item) for item in data]
    if isinstance(data, str):
        return repair_text(data)
    return data


async def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )


def format_ms(value: Any) -> str:
    try:
        total = int(value) // 1000
    except Exception:
        return ""
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def extract_subtitle_records(data: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if {"res", "bg", "ed"}.issubset(data.keys()):
            records.append(data)
        for value in data.values():
            records.extend(extract_subtitle_records(value))
    elif isinstance(data, list):
        for item in data:
            records.extend(extract_subtitle_records(item))
    return records


def records_to_text(records: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for record in records:
        text = str(record.get("res") or "").strip()
        if not text:
            continue
        begin = format_ms(record.get("bg"))
        end = format_ms(record.get("ed"))
        line = f"[{begin}-{end}] {text}" if begin and end else text
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def get_response_json(captured: list[dict[str, Any]], path: str) -> Any | None:
    for item in captured:
        if path in item.get("url", ""):
            return item.get("json")
    return None


LESSON_LIST_PATHS = (
    "/v1/subject_vod_list",
    "/v1/group_subject_vod_list",
)


def extract_lesson_records(captured: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for path in LESSON_LIST_PATHS:
        data = get_response_json(captured, path)
        if isinstance(data, dict):
            records = data.get("data", {}).get("records", [])
            if isinstance(records, list) and records:
                return records
    return []


def compact_lesson(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "teclId": record.get("teclId"),
        "subjName": record.get("subjName"),
        "teacNames": record.get("teacNames"),
        "teclName": record.get("teclName"),
        "teclCode": record.get("teclCode"),
        "courBeginTime": record.get("courBeginTime"),
        "courEndTime": record.get("courEndTime"),
        "letiNumber": record.get("letiNumber"),
        "zc": record.get("zc"),
        "xqj": record.get("xqj"),
        "clroName": record.get("clroName"),
        "courTransferFlag": record.get("courTransferFlag"),
        "courVodOpen": record.get("courVodOpen"),
        "vodEnable": record.get("vodEnable"),
        "vodStatus": record.get("vodStatus"),
        "watchPercent": record.get("watchPercent"),
    }


def build_course_info(lessons: list[dict[str, Any]]) -> dict[str, Any]:
    if not lessons:
        return {}
    first = lessons[0]
    return {
        "subjName": first.get("subjName"),
        "teacNames": first.get("teacNames"),
        "teclId": first.get("teclId"),
        "teclName": first.get("teclName"),
        "teclCode": first.get("teclCode"),
        "total_lessons": len(lessons),
        "transferable_lessons": sum(1 for r in lessons if r.get("courTransferFlag")),
        "date_range": {
            "first": min((r.get("courBeginTime") or "" for r in lessons), default=""),
            "last": max((r.get("courEndTime") or "" for r in lessons), default=""),
        },
    }


def summarize_inventory(captured: list[dict[str, Any]]) -> dict[str, Any]:
    by_path: dict[str, int] = {}
    for item in captured:
        path = urlparse(item["url"]).path
        by_path[path] = by_path.get(path, 0) + 1
    lesson_records = extract_lesson_records(captured)
    return {
        "response_counts": by_path,
        "lesson_count": len(lesson_records),
        "transferable_lesson_count": sum(
            1 for r in lesson_records if r.get("courTransferFlag")
        ),
        "lessons": [compact_lesson(r) for r in lesson_records],
    }


async def fetch_json_from_page(
    page: Page, path: str, params: dict[str, Any]
) -> dict[str, Any]:
    return await page.evaluate(
        """async ({ path, params }) => {
            const url = new URL(path, window.location.origin);
            for (const [key, value] of Object.entries(params || {})) {
                if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
            }
            const response = await fetch(url.toString(), { credentials: "include" });
            const text = await response.text();
            let body;
            try { body = JSON.parse(text); } catch (_) { body = text; }
            return { url: url.toString(), status: response.status, ok: response.ok, body };
        }""",
        {"path": path, "params": params},
    )


async def fetch_subtitle_for_lesson(
    page: Page, lesson: dict[str, Any], output_dir: Path
) -> bool:
    """Fetch subtitle for one lesson and write transcript to its directory."""
    lesson_id = lesson["id"]
    lesson_dir = output_dir / "lessons" / str(lesson_id)
    raw_dir = lesson_dir / "raw"

    if (raw_dir / "transcript.txt").exists():
        return True

    result = await fetch_json_from_page(
        page,
        f"{_api_base}/v1/course_vod_subtitle",
        {"courseId": lesson_id},
    )

    body = repair_json_text(result["body"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    await write_json(lesson_dir / "metadata.json", compact_lesson(lesson))
    await write_json(raw_dir / "subtitle.json", body)

    records = extract_subtitle_records(body)
    if not records:
        return False

    text = records_to_text(records)
    if not text.strip():
        return False

    (raw_dir / "transcript.txt").write_text(text + "\n", encoding="utf-8")

    semantic_dir = lesson_dir / "semantic_rebuild"
    semantic_dir.mkdir(parents=True, exist_ok=True)
    semantic_input = {
        "source": "nuaa-vod",
        "lesson_id": lesson_id,
        "subjName": lesson.get("subjName"),
        "teacNames": lesson.get("teacNames"),
        "courBeginTime": lesson.get("courBeginTime"),
        "courEndTime": lesson.get("courEndTime"),
        "letiNumber": lesson.get("letiNumber"),
        "zc": lesson.get("zc"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcript_path": str(raw_dir / "transcript.txt"),
        "notes": [
            "Transcript text extracted from NUAA VOD subtitle API.",
            "Review before treating as final course material.",
        ],
    }
    await write_json(semantic_dir / "semantic_rebuild_input.json", semantic_input)
    (semantic_dir / "semantic_rebuild_prompt.md").write_text(
        "# Semantic rebuild prompt\n\n"
        "Read `semantic_rebuild_input.json` and `../raw/transcript.txt`.\n"
        "Write a student-facing Markdown course note in Chinese.\n\n"
        "## Required sections\n"
        "- 本节主线 (2-4 sentence summary)\n"
        "- 时间轴 (table, 5-10 min granularity)\n"
        "- 关键概念 (term + one-line explanation each)\n"
        "- 要点详述 (topic-by-topic restatement, NOT verbatim ASR)\n"
        "- 作业/考试/通知 (only if explicitly mentioned)\n"
        "- 待核对 (garbled/unclear parts)\n"
        "- 回看建议 (timestamped review suggestions)\n\n"
        "## Rules\n"
        "- Never invent content; everything must be traceable to the transcript.\n"
        "- Rephrase in your own words; do not copy ASR output as final prose.\n"
        "- Use [MM:SS] timestamps when referencing specific moments.\n"
        "- Do not expose API fields, internal paths, or workflow details.\n",
        encoding="utf-8",
    )
    return True


async def probe_lesson_list(
    page: Page, captured: list[dict[str, Any]]
) -> None:
    """Proactively fetch lesson list from known API endpoints."""
    for path in LESSON_LIST_PATHS:
        full_path = f"{_api_base}{path}"
        try:
            result = await fetch_json_from_page(page, full_path, {})
        except Exception:
            continue
        if not result.get("ok"):
            continue
        body = result["body"]
        if isinstance(body, dict) and body.get("data", {}).get("records"):
            captured.append({
                "url": result["url"],
                "status": result["status"],
                "ok": result["ok"],
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "json": repair_json_text(body),
            })
            return


async def collect_lessons_to_extract(
    page: Page, captured: list[dict[str, Any]], args: argparse.Namespace
) -> list[dict[str, Any]]:
    """Determine which lessons to extract subtitles for."""
    all_lessons = extract_lesson_records(captured)

    if args.subtitle_course_id:
        for r in all_lessons:
            if str(r.get("id")) == str(args.subtitle_course_id):
                return [r]
        print(f"Lesson {args.subtitle_course_id} not found in lesson list.", file=sys.stderr)
        return []

    transferable = [r for r in all_lessons if r.get("courTransferFlag")]

    if args.batch:
        return transferable

    return transferable[: args.probe_subtitle_count]


async def extract_lessons(
    page: Page, lessons: list[dict[str, Any]], output_dir: Path, skip_existing: bool
) -> dict[str, Any]:
    """Extract subtitles for selected lessons. Returns summary stats."""
    stats = {"total": len(lessons), "success": 0, "no_subtitle": 0, "skipped": 0}

    for i, lesson in enumerate(lessons):
        lesson_id = lesson["id"]
        begin = lesson.get("courBeginTime", "")[:10]
        name = lesson.get("subjName", "")
        leti = lesson.get("letiNumber", "")
        label = f"{name} 第{leti}节 ({begin})"

        transcript_path = output_dir / "lessons" / str(lesson_id) / "raw" / "transcript.txt"
        if skip_existing and transcript_path.exists():
            print(f"[{i+1}/{len(lessons)}] SKIP {label} (already exists)")
            stats["skipped"] += 1
            continue

        print(f"[{i+1}/{len(lessons)}] {label} ...", end=" ", flush=True)
        ok = await fetch_subtitle_for_lesson(page, lesson, output_dir)
        if ok:
            print("OK")
            stats["success"] += 1
        else:
            print("no subtitle")
            stats["no_subtitle"] += 1

    return stats


async def wait_for_manual_login_seconds(seconds: int) -> None:
    if seconds <= 0:
        return
    print(f"Waiting {seconds} second(s) for manual login/page load...", flush=True)
    await asyncio.sleep(seconds)


async def setup_capture(page: Page, captured: list[dict[str, Any]]) -> None:
    async def on_response(response):
        url = response.url
        if not is_interesting_url(url):
            return
        item: dict[str, Any] = {
            "url": url,
            "status": response.status,
            "ok": response.ok,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            item["json"] = repair_json_text(await response.json())
        except Exception:
            try:
                text = await response.text()
            except Exception as exc:
                text = f"<unable to read response text: {exc}>"
            item["text"] = repair_text(text[:20000])
        captured.append(item)

    page.on("response", on_response)


async def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    page_info = parse_video_detail_url(args.url)
    await write_json(raw_dir / "page.json", page_info)

    args.url = normalize_url(args.url)

    captured: list[dict[str, Any]] = []

    async with async_playwright() as p:
        user_data_dir = (
            Path(args.user_data_dir).resolve()
            if args.user_data_dir
            else output_dir / ".browser-profile"
        )
        browser_channel = None if args.browser_channel == "chromium" else args.browser_channel
        context: BrowserContext = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=not args.browser_runtime_auth,
            channel=browser_channel,
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await setup_capture(page, captured)

        await page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        if args.browser_runtime_auth:
            print(
                "Browser open. Complete NUAA login and wait for the course page to load.",
                flush=True,
            )
            await wait_for_manual_login_seconds(args.manual_wait_seconds)

        await page.wait_for_load_state("networkidle", timeout=args.timeout_ms)
        await page.wait_for_timeout(args.extra_wait_ms)

        if not captured:
            await probe_lesson_list(page, captured)

        lessons_to_extract = await collect_lessons_to_extract(page, captured, args)
        stats = await extract_lessons(page, lessons_to_extract, output_dir, args.skip_existing)

        storage_state = await context.storage_state()
        await write_json(raw_dir / "storage_state.json", storage_state)
        await context.close()

    await write_json(raw_dir / "captured_responses.json", captured)

    inventory = summarize_inventory(captured)
    await write_json(output_dir / "replay_inventory.json", inventory)

    course_info = build_course_info(extract_lesson_records(captured))
    await write_json(output_dir / "course.json", course_info)

    for index, item in enumerate(captured, start=1):
        path = safe_filename(urlparse(item["url"]).path)
        await write_json(raw_dir / "responses" / f"{index:03d}_{path}.json", item)

    if not captured:
        print("No NUAA VOD API responses captured. Confirm login and page access.", file=sys.stderr)
        return 2

    course_name = course_info.get("subjName", "Unknown")
    print(f"Course: {course_name}")
    print(f"Lessons total: {inventory['lesson_count']}, transferable: {inventory['transferable_lesson_count']}")
    print(f"Extracted: {stats['success']} success, {stats['no_subtitle']} no-subtitle, {stats['skipped']} skipped")
    print(f"Captured {len(captured)} API response(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract NUAA Feitian Cloud Classroom VOD artifacts.")
    parser.add_argument("url", help="NUAA video-detail URL.")
    parser.add_argument("--output-dir", required=True, help="Directory for extraction artifacts.")
    parser.add_argument("--browser-runtime-auth", action="store_true", help="Open visible browser for manual login.")
    parser.add_argument(
        "--manual-wait-seconds",
        type=int,
        default=0,
        help="Keep browser open for this many seconds before extraction.",
    )
    parser.add_argument("--user-data-dir", help="Persistent Playwright user data directory.")
    parser.add_argument("--browser-channel", default="msedge", help="Chromium channel: msedge, chrome, or chromium.")
    parser.add_argument("--timeout-ms", type=int, default=60000)
    parser.add_argument("--extra-wait-ms", type=int, default=5000)
    parser.add_argument("--login-timeout-seconds", type=int, default=180)
    parser.add_argument("--subtitle-course-id", help="Extract a specific lesson by course ID.")
    parser.add_argument(
        "--probe-subtitle-count",
        type=int,
        default=1,
        help="Number of transferable lessons to probe (default 1, ignored with --batch).",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Extract ALL transferable lessons instead of probing a few.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip lessons that already have a transcript file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
