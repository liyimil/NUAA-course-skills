#!/usr/bin/env python3
"""Multi-course management for NUAA Course Skills.

Usage:
  python manage.py add "<video-detail-url>"     Register and extract a new course
  python manage.py list                          List all registered courses
  python manage.py status <course-name>          Show detailed status for one course
  python manage.py extract <course-name>         Re-extract VOD data for a course
  python manage.py sync <course-name>            Sync course to Obsidian vault
  python manage.py vault-init                    Initialize Obsidian vault
  python manage.py vault-sync-all                Sync all courses to vault
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = REPO_ROOT / "courses.json"
DEFAULT_VAULT_DIR = REPO_ROOT / "vault"


def load_registry() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"courses": {}, "vault_dir": str(DEFAULT_VAULT_DIR)}


def save_registry(reg: dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_course_key(reg: dict[str, Any], name_or_url: str) -> str | None:
    """Find course key by name, teclId, or URL fragment."""
    courses = reg.get("courses", {})
    if name_or_url in courses:
        return name_or_url
    for key, info in courses.items():
        if name_or_url in info.get("url", ""):
            return key
        if name_or_url == str(info.get("teclId", "")):
            return key
    return None


def cmd_add(args: argparse.Namespace) -> int:
    """Extract a new course from a video-detail URL and register it."""
    url = args.url

    # Quick probe to discover course identity
    extract_script = REPO_ROOT / "skills" / "nuaa-vod-summarizer" / "scripts" / "extract_nuaa_vod.py"
    if not extract_script.exists():
        print("ERROR: nuaa-vod-summarizer skill not found.", file=sys.stderr)
        return 1

    reg = load_registry()

    # Check if URL already registered
    for key, info in reg.get("courses", {}).items():
        if info.get("url") == url:
            print(f"Course already registered as '{key}'.")
            print(f"Use 'python manage.py extract {key}' to re-extract.")
            return 0

    # Extract VOD data first (this will create course.json)
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(url)
    fragment = parsed.fragment or ""
    _, _, query = fragment.partition("?")
    params = parse_qs(query)
    tecl_id = (params.get("id") or params.get("teclId") or [None])[-1] or "unknown"

    output_dir = REPO_ROOT / "work" / tecl_id
    print(f"Extracting from: {url}")
    print(f"Output directory: {output_dir}")
    print()

    extract_args = [
        sys.executable, str(extract_script), url,
        "--output-dir", str(output_dir),
        "--browser-runtime-auth",
        "--manual-wait-seconds", str(args.wait or 120),
        "--extra-wait-ms", "8000",
        "--batch",
    ]
    if args.skip_existing:
        extract_args.append("--skip-existing")

    result = subprocess.run(extract_args, cwd=str(extract_script.parent.parent))
    if result.returncode != 0:
        print("Extraction failed.", file=sys.stderr)
        return result.returncode

    # Read discovered course info
    course_json = output_dir / "course.json"
    if not course_json.exists():
        print("WARNING: course.json not found. Course registered with teclId as name.")
        course_name = f"course-{tecl_id}"
    else:
        info = json.loads(course_json.read_text(encoding="utf-8"))
        course_name = info.get("subjName") or f"course-{tecl_id}"

    # Register
    reg["courses"][course_name] = {
        "url": url,
        "teclId": tecl_id,
        "vod_output_dir": str(output_dir),
        "course_name": course_name,
    }
    save_registry(reg)

    print(f"\nCourse registered: {course_name}")
    print(f"Next: python manage.py sync \"{course_name}\"")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all registered courses."""
    reg = load_registry()
    courses = reg.get("courses", {})
    if not courses:
        print("No courses registered yet.")
        print(f"Add one: python manage.py add \"https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=XXXXX\"")
        return 0

    print(f"{'Course':<16} {'teclId':<10} {'Finished':<10} {'Pending':<10} {'Vault'}")
    print("-" * 72)
    for name, info in sorted(courses.items()):
        vod_dir = Path(info["vod_output_dir"])
        notes = 0
        backlog = 0
        in_vault = "no"
        if vod_dir.exists():
            lessons_dir = vod_dir / "lessons"
            if lessons_dir.is_dir():
                for lesson_dir in lessons_dir.iterdir():
                    if (lesson_dir / "note.md").exists():
                        notes += 1
            inventory_path = vod_dir / "replay_inventory.json"
            if inventory_path.exists():
                inv = json.loads(inventory_path.read_text(encoding="utf-8"))
                transferable = sum(1 for r in inv.get("lessons", []) if r.get("courTransferFlag"))
                backlog = transferable - notes

        vault_dir = Path(reg.get("vault_dir", ""))
        course_dir = vault_dir / "01-Courses" / name
        if course_dir.is_dir():
            in_vault = "yes"

        print(f"{name:<16} {info.get('teclId', ''):<10} {notes:<10} {backlog:<10} {in_vault}")

    vault_dir = reg.get("vault_dir", "not set")
    print(f"\nVault: {vault_dir}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show detailed status for one course."""
    reg = load_registry()
    key = resolve_course_key(reg, args.course)
    if key is None:
        print(f"Course '{args.course}' not found in registry.", file=sys.stderr)
        print("Use 'python manage.py list' to see registered courses.", file=sys.stderr)
        return 1

    info = reg["courses"][key]
    vod_dir = Path(info["vod_output_dir"])
    print(f"Course: {key}")
    print(f"  URL: {info['url']}")
    print(f"  teclId: {info['teclId']}")
    print(f"  VOD dir: {vod_dir}")

    if not vod_dir.exists():
        print("  VOD data: not extracted yet")
        return 0

    course_json = vod_dir / "course.json"
    if course_json.exists():
        c = json.loads(course_json.read_text(encoding="utf-8"))
        print(f"  Teacher: {', '.join(c.get('teacNames', []))}")
        print(f"  Total lessons: {c.get('total_lessons', '?')}")
        print(f"  Transferable: {c.get('transferable_lessons', '?')}")

    lessons_dir = vod_dir / "lessons"
    if lessons_dir.is_dir():
        lesson_dirs = list(lessons_dir.iterdir())
        finished = sum(1 for d in lesson_dirs if (d / "note.md").exists())
        print(f"  Lessons extracted: {len(lesson_dirs)}")
        print(f"  Notes finished: {finished}")
        if finished > 0:
            print("  Finished lessons:")
            for d in sorted(lesson_dirs):
                note = d / "note.md"
                if note.exists():
                    meta_path = d / "metadata.json"
                    if meta_path.exists():
                        m = json.loads(meta_path.read_text(encoding="utf-8"))
                        print(f"    [{m.get('courBeginTime', '')[:10]}] 第{m.get('letiNumber', '')}节  {d.name}")

    vault_dir = Path(reg.get("vault_dir", ""))
    course_vault_dir = vault_dir / "01-Courses" / key
    print(f"  In vault: {'yes' if course_vault_dir.is_dir() else 'no'}")

    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync a course to the Obsidian vault."""
    reg = load_registry()
    key = resolve_course_key(reg, args.course)
    if key is None:
        print(f"Course '{args.course}' not found.", file=sys.stderr)
        return 1

    info = reg["courses"][key]
    vault_dir = Path(reg.get("vault_dir", str(DEFAULT_VAULT_DIR)))

    sync_script = REPO_ROOT / "skills" / "obsidian-course-vault" / "scripts" / "sync_nuaa_course.py"
    add_script = REPO_ROOT / "skills" / "obsidian-course-vault" / "scripts" / "add_course.py"

    # Ensure course exists in vault
    course_dir = vault_dir / "01-Courses" / key
    if not course_dir.is_dir():
        print(f"Adding '{key}' to vault...")
        subprocess.run(
            [sys.executable, str(add_script), "--vault-dir", str(vault_dir), "--course-name", key],
            check=True,
        )

    sync_args = [
        sys.executable, str(sync_script),
        "--vault-dir", str(vault_dir),
        "--course-name", key,
        "--vod-output-dir", info["vod_output_dir"],
    ]
    if args.force:
        sync_args.append("--force")

    result = subprocess.run(sync_args)
    return result.returncode


def cmd_vault_init(args: argparse.Namespace) -> int:
    """Initialize the Obsidian vault."""
    reg = load_registry()
    vault_dir = Path(reg.get("vault_dir", str(DEFAULT_VAULT_DIR)))

    init_script = REPO_ROOT / "skills" / "obsidian-course-vault" / "scripts" / "init_obsidian_course_vault.py"
    result = subprocess.run(
        [sys.executable, str(init_script), "--vault-dir", str(vault_dir)],
    )
    if result.returncode == 0:
        reg["vault_dir"] = str(vault_dir)
        save_registry(reg)
    return result.returncode


def cmd_vault_sync_all(args: argparse.Namespace) -> int:
    """Sync all registered courses to the vault."""
    reg = load_registry()
    courses = reg.get("courses", {})
    if not courses:
        print("No courses registered.")
        return 0

    vault_dir = Path(reg.get("vault_dir", str(DEFAULT_VAULT_DIR)))
    if not (vault_dir / ".obsidian").is_dir():
        print("Vault not initialized. Run 'python manage.py vault-init' first.")
        return 1

    failed = 0
    for name in sorted(courses):
        print(f"\n--- Syncing {name} ---")
        result = subprocess.run([
            sys.executable, __file__, "sync", name,
        ])
        if result.returncode != 0:
            failed += 1

    print(f"\nSynced {len(courses) - failed}/{len(courses)} courses.")
    return 0 if failed == 0 else 1


def cmd_extract(args: argparse.Namespace) -> int:
    """Re-extract VOD data for a registered course."""
    reg = load_registry()
    key = resolve_course_key(reg, args.course)
    if key is None:
        print(f"Course '{args.course}' not found.", file=sys.stderr)
        return 1

    info = reg["courses"][key]
    extract_script = REPO_ROOT / "skills" / "nuaa-vod-summarizer" / "scripts" / "extract_nuaa_vod.py"
    extract_args = [
        sys.executable, str(extract_script), info["url"],
        "--output-dir", info["vod_output_dir"],
        "--browser-runtime-auth",
        "--manual-wait-seconds", str(args.wait or 10),
        "--extra-wait-ms", "8000",
        "--batch",
    ]
    if args.skip_existing:
        extract_args.append("--skip-existing")

    result = subprocess.run(extract_args, cwd=str(extract_script.parent.parent))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NUAA Course Skills — multi-course manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py add "https://ft.nuaa.edu.cn/.../#/video-detail?id=118467"
  python manage.py list
  python manage.py status 操作系统
  python manage.py extract 操作系统 --skip-existing
  python manage.py sync 操作系统
  python manage.py vault-init
  python manage.py vault-sync-all
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    p_add = subparsers.add_parser("add", help="Register and extract a new course")
    p_add.add_argument("url", help="NUAA video-detail URL")
    p_add.add_argument("--wait", type=int, default=120, help="Login wait time in seconds")
    p_add.add_argument("--skip-existing", action="store_true")

    subparsers.add_parser("list", help="List all registered courses")

    p_status = subparsers.add_parser("status", help="Show detailed status for a course")
    p_status.add_argument("course", help="Course name, teclId, or URL fragment")

    p_extract = subparsers.add_parser("extract", help="Re-extract VOD data for a course")
    p_extract.add_argument("course", help="Course name, teclId, or URL fragment")
    p_extract.add_argument("--wait", type=int, default=10, help="Login wait time in seconds")
    p_extract.add_argument("--skip-existing", action="store_true")

    p_sync = subparsers.add_parser("sync", help="Sync a course to Obsidian vault")
    p_sync.add_argument("course", help="Course name, teclId, or URL fragment")
    p_sync.add_argument("--force", action="store_true")

    subparsers.add_parser("vault-init", help="Initialize Obsidian vault")
    subparsers.add_parser("vault-sync-all", help="Sync all courses to vault")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0

    handlers = {
        "add": cmd_add,
        "list": cmd_list,
        "status": cmd_status,
        "extract": cmd_extract,
        "sync": cmd_sync,
        "vault-init": cmd_vault_init,
        "vault-sync-all": cmd_vault_sync_all,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
