#!/usr/bin/env python3
"""Initialize an Obsidian course vault with standard NUAA structure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HOME_NOTE = """# 课程知识库

## 使用方式

- 在 `01-Courses` 里维护每门课。
- 在 `02-Concepts` 里沉淀跨课次概念。
- 在 `03-Admin` 里汇总作业、考试、通知。
- 在 `05-Inbox` 里放待整理草稿。
- 知识图谱建议只看 `02-Concepts`，并按课程文件夹过滤。

## 快速入口

- [[03-Admin/作业总表]]
- [[03-Admin/考试与通知]]
- [[04-Templates/课程总览模板]]
- [[04-Templates/课次纪要模板]]
- [[04-Templates/概念模板]]
"""

ASSIGNMENTS_NOTE = """# 作业总表

| 课程 | 日期 | 内容 | 截止时间 | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
"""

EXAMS_NOTE = """# 考试与通知

## 考试

| 课程 | 日期 | 类型 | 范围 | 备注 |
| --- | --- | --- | --- | --- |

## 通知

| 课程 | 日期 | 内容 | 备注 |
| --- | --- | --- | --- |
"""

GRAPH_GUIDE = """# 知识图谱使用规范

## 原则

- 知识图谱只承载"概念"。
- 课次笔记、作业、通知不作为图谱中心。
- 一张成熟的课程图谱应有"章节枢纽"，而不只是平铺概念名。

## 建议做法

- 把概念页集中放在 `02-Concepts/课程名`。
- 每门课至少维护一张总图谱页，再按章节维护若干张知识地图页。
- 概念页正文尽量只保留概念内容，课程、章节、首次出现课次等信息放进 frontmatter。
- 在 Obsidian 里看图谱建议过滤：`path:"02-Concepts/课程名"`
"""

COURSE_TEMPLATE = """---
course: {{course_name}}
semester:
teacher:
---

# {{course_name}}

## 课程信息

- 学期：
- 教师：
- 教材：
- 考核方式：

## 章节地图

- 图谱入口：[[../02-Concepts/{{course_name}}/{{course_name}}概念图谱]]
- 第一部分：
- 第二部分：
- 第三部分：

## 课次索引

-

## 核心概念

-

## 课程事务

- [[事务]]
- [[已整理课次]]
- [[待整理回放]]
- [[待回看问题]]
- [[章节完成度]]
"""

LESSON_TEMPLATE = """---
type: lesson
course: {{course_name}}
title: {{lesson_title}}
date:
concepts: []
---

# {{lesson_title}}

## 元信息

- 课程：[[../00-课程总览]]
- 日期：
- 节次：

## 本节主线

-

## 内容纪要

### 主题 1

时间参考：

-

## 课程事务

### 作业

-

### 考试

-

### 通知

-

## 本节提到的概念

-

## 待核对

-
"""

CONCEPT_TEMPLATE = """---
type: concept
course: {{course_name}}
chapter: []
first_seen:
prerequisites: []
related: []
contrasts: []
---

# {{concept_name}}

## 定义

-

## 直觉理解

-

## 前置概念

-

## 推导到 / 关联到

-

## 易混概念

-

## 典型例子

-
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def ensure_obsidian_ignore_filters(vault_dir: Path) -> None:
    app_json = vault_dir / ".obsidian" / "app.json"
    app_json.parent.mkdir(parents=True, exist_ok=True)
    if app_json.exists():
        try:
            config = json.loads(app_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}
    if not isinstance(config, dict):
        config = {}
    current = config.get("userIgnoreFilters", [])
    if not isinstance(current, list):
        current = []
    filters = [str(item) for item in current if str(item).strip()]
    for pattern in ["**/.course-internal/**", "**/semantic_rebuild/**"]:
        if pattern not in filters:
            filters.append(pattern)
    config["userIgnoreFilters"] = filters
    app_json.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize an Obsidian course vault.")
    parser.add_argument("--vault-dir", required=True, help="Directory for the Obsidian vault.")
    args = parser.parse_args()

    vault_dir = Path(args.vault_dir).resolve()

    dirs = [
        vault_dir / ".obsidian",
        vault_dir / "01-Courses",
        vault_dir / "02-Concepts",
        vault_dir / "03-Admin",
        vault_dir / "04-Templates",
        vault_dir / "05-Inbox",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    ensure_obsidian_ignore_filters(vault_dir)

    write_text(vault_dir / "00-Home.md", HOME_NOTE)
    write_text(vault_dir / "03-Admin" / "作业总表.md", ASSIGNMENTS_NOTE)
    write_text(vault_dir / "03-Admin" / "考试与通知.md", EXAMS_NOTE)
    write_text(vault_dir / "03-Admin" / "知识图谱使用规范.md", GRAPH_GUIDE)
    write_text(vault_dir / "04-Templates" / "课程总览模板.md", COURSE_TEMPLATE)
    write_text(vault_dir / "04-Templates" / "课次纪要模板.md", LESSON_TEMPLATE)
    write_text(vault_dir / "04-Templates" / "概念模板.md", CONCEPT_TEMPLATE)

    meta = {
        "vault_dir": str(vault_dir),
        "initialized_by": "nuaa-obsidian-course-vault",
    }
    write_text(
        vault_dir / ".obsidian" / "course-vault.json",
        json.dumps(meta, ensure_ascii=False, indent=2),
    )

    print(f"Vault initialized at: {vault_dir}")
    print("Open this folder as an Obsidian vault to get started.")


if __name__ == "__main__":
    main()
