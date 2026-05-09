# NUAA Course Skills

把南航飞天云课堂的课程点播、AI 字幕、课件和课次元信息自动抓取下来，整理成可检索、可复习的结构化笔记，支持同步到 Obsidian 长期知识库。

## 做了什么

- 浏览器自动化登录南航飞天云课堂，枚举全部课次
- 自动识别有 AI 字幕的课次，批量拉取字幕/转写文本
- 基于字幕生成结构化课堂笔记（搭配 Claude Code / ChatGPT 等 AI 工具）
- 一键同步到 Obsidian vault，按课程/课次组织

## 环境要求

- Python 3.10+
- 南航统一认证账号
- （可选）[Obsidian](https://obsidian.md/) — 用于知识库管理

## 快速开始

```powershell
# 1. 克隆仓库
git clone https://github.com/liyimil/NUAA-course-skills.git
cd NUAA-course-skills

# 2. 复制课程表模板
copy courses.example.json courses.json

# 3. 安装依赖
cd skills\nuaa-vod-summarizer
python -m pip install -r requirements.txt
python -m playwright install chromium
cd ..\..

# 4. 初始化 Obsidian vault（可选）
python manage.py vault-init
```

## 日常使用

### 添加一门课

打开南航飞天云课堂，找到课程的 `video-detail` 页面，复制 URL：

```powershell
python manage.py add "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=118467"
```

浏览器会自动打开。在窗口里完成南航统一认证登录，脚本会自动完成：
- 枚举全部课次
- 识别哪些课次有 AI 字幕
- 批量拉取字幕（增量，已拉过的跳过）

### 查看状态

```powershell
python manage.py list              # 所有课程一览
python manage.py status 操作系统    # 单门课详情
```

### 后续增量抽取

Cookie 过期前不用重新登录：

```powershell
python manage.py extract 操作系统 --skip-existing
```

### 生成笔记

每节课的字幕拉下来后，在 `work/<teclId>/lessons/<lessonId>/semantic_rebuild/` 下有 AI 字幕文本。用 AI 工具读取每课的 transcript 生成笔记：

1. 在 Claude Code 中打开项目目录
2. 找到对应课次的 `semantic_rebuild_input.json`（含字幕 + 课件提示）
3. 让 AI 读取并生成 `note.md`

或者用脚本批量处理：

```powershell
cd skills\nuaa-vod-summarizer
python scripts\generate_note.py --course-dir ..\..\work\118467 --lesson-id 1547370
```

### 同步到 Obsidian

写完笔记后：

```powershell
python manage.py sync 操作系统        # 同步单门课
python manage.py vault-sync-all       # 同步全部课程
```

同步会自动更新 vault 中的课程总览、课次索引、已完成/待整理列表。

## 项目结构

```
NUAA-course-skills/
  manage.py                         # 多课程管理入口
  courses.example.json              # 课程表模板
  skills/
    nuaa-vod-summarizer/            # VOD 字幕抽取
      scripts/
        extract_nuaa_vod.py         #   核心抽取脚本
        generate_note.py            #   笔记生成脚本
      requirements.txt
    obsidian-course-vault/          # Obsidian 课程库
      scripts/
        init_obsidian_course_vault.py
        add_course.py
        sync_nuaa_course.py
  work/<teclId>/                    # 抽取数据（不提交到 git）
    lessons/<lessonId>/
      raw/                          #   原始字幕+课件响应
      semantic_rebuild/             #   可供 AI 读取的结构化输入
      note.md                       #   生成的笔记
```

## Vault 结构

```
vault/
  00-Home.md
  01-Courses/
    操作系统/
      00-课程总览.md                # 课程元信息 + 课次索引
      已整理课次.md                  # 已完成笔记一览
      待整理回放.md                  # 待写笔记的课次
      事务.md                       # 作业/考试/通知汇总
      课次/
        2026-03-09 操作系统 第2节.md
  02-Concepts/                     # 跨课程概念索引
  03-Admin/                        # 作业总表、考试通知
```

## 常见问题

**浏览器打开了但没反应？**
确认已在浏览器窗口完成南航统一认证登录，脚本会等页面加载完成后自动继续。

**提示 401 或登录失效？**
Cookie 过期了，重新跑 `python manage.py extract <课程名>` 会重新打开浏览器让你登录。

**只想用字幕不想用 Obsidian？**
完全没问题，`work/<teclId>/` 下的 transcript 文本独立可用，跳过 vault-init 和 sync 步骤即可。

**怎么支持第二门课？**
直接 `python manage.py add "<新的 video-detail URL>"` 即可，多门课共用一个 vault。
