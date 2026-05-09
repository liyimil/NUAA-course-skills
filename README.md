# NUAA Course Skills

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-public%20beta-yellow)](https://github.com/liyimil/NUAA-course-skills)
[![GitHub last commit](https://img.shields.io/github/last-commit/liyimil/NUAA-course-skills)](https://github.com/liyimil/NUAA-course-skills)

把南航飞天云课堂的课程点播、AI 字幕、课件和课次元信息，整理成**可检索、可回看、可复用**的课程学习资料。

它既可以生成单次课程笔记，也可以沉淀到 Obsidian，形成长期维护的课程知识库。

如果你属于下面这类人，这个仓库大概率会有用：

- 想系统复盘一门课，而不是只看单节回放
- 上课跟得不稳定，但又不想完全掉队
- 想快速知道老师这节课讲了什么、强调了什么、布置了什么
- 希望把一门课长期整理成自己的知识库
- 已经在用 Obsidian，想把课程笔记、概念页和图谱结构一起长出来

这套 skill 想做的不是"替你听课"，而是把课堂内容整理成一种更容易进入的学习资料。很多用户并不缺课堂回放，而是缺一个比"再听一遍课"更容易吸收的入口。

## 这个仓库解决什么问题

课堂回放通常能播放，但不容易真正用于复习：

- 过几周后，很难快速回忆某一节课到底讲了什么
- 想回看某个知识点时，不知道应该从哪一段开始
- 老师提到的作业、考试、练习和提醒，分散在整节课里
- 一学期结束后，留下的往往是一堆零散转写，而不是结构化课程资料

这个仓库的目标，是把"能播放的课堂回放"变成"可以长期复用的学习资料"。

## 仓库包含两个 skill

### `nuaa-vod-summarizer`

从南航飞天云课堂 `video-detail` 或 `play-center` 页面提取结构化回放原料，并生成单次课程笔记。

适合你想要：

- 枚举可回放课次
- 提取 AI 字幕和课次元信息
- 批量拉取课程转写文本
- 基于字幕生成结构化 Markdown 笔记

### `obsidian-course-vault`

把课程原料和课次笔记整理进 Obsidian，维护课程总览、课次页、概念页和图谱 hub。

适合你想要：

- 持续维护一门课的知识库
- 把单节课笔记逐渐长成课程体系
- 在 Obsidian 中建立概念页、图谱入口和课程总览

## 正式支持的输入入口

当前正式支持：

- `ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=...`
- `ft.nuaa.edu.cn/jy-application-resourcemanage-ui/#/play-center?teclId=...`

API base 从 URL 自动检测。

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

也可以通过 `npx skills add` 安装单个 skill：

```bash
npx skills add https://github.com/liyimil/NUAA-course-skills --skill nuaa-vod-summarizer --yes --global
npx skills add https://github.com/liyimil/NUAA-course-skills --skill obsidian-course-vault --yes --global
```

安装完成后，请到安装后的 skill 目录补充 `requirements.txt` 依赖。详细说明见 [INSTALL.md](INSTALL.md)。

## 日常使用

### 添加一门课

```powershell
python manage.py add "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=118467"
```

浏览器会自动打开，在窗口里完成南航统一认证登录后脚本自动完成课次枚举和字幕拉取。

### 后续增量抽取

```powershell
python manage.py extract 操作系统 --skip-existing
```

### 查看状态

```powershell
python manage.py list              # 所有课程一览
python manage.py status 操作系统    # 单门课详情
```

### 生成笔记

每节课的字幕拉下来后，在 `work/<teclId>/lessons/<lessonId>/semantic_rebuild/` 下有结构化输入包。用 AI 工具读取每课的字幕文本生成 `note.md`：

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

## 推荐用法

### 方案 A：只做字幕抽取和笔记生成

使用 `nuaa-vod-summarizer` 就够了。

适合你想要：

- 枚举可回放课次
- 批量拉取 AI 字幕和转写文本
- 基于字幕生成独立 Markdown 笔记
- 先把一门课安全地做成"可继续整理的原料和单节输出"

### 方案 B：做完整课程知识库

两个 skill 一起用。

适合你想要：

- 持续维护的 Obsidian 课程库
- 能点开的概念页
- 可读的图谱 hub 和课程总览
- 一学期持续同步和整理回放

## 你最终会得到什么

使用 `nuaa-vod-summarizer` 时，典型输出包括：

- 一份按课次组织的 Markdown 笔记
- 本节主线总结
- 带时间戳的内容时间轴
- 关键概念整理
- 课程事务 / 作业 / 待核对信息
- 面向复习的回看建议

如果再配合 `obsidian-course-vault`，还可以继续维护：

- 课程总览页
- 已整理课次 / 待整理回放列表
- 概念页
- 课程图谱 hub
- 作业总表与考试通知

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


## 首次使用建议

第一次使用时，建议不要一上来就整学期全量落库。

更稳的顺序是：

1. 先安装 `nuaa-vod-summarizer` 依赖
2. 先拿一节课或一门课跑通抽取
3. 确认登录态、输出目录、字幕状态都正常
4. 再接 `obsidian-course-vault`

## 当前不太适合的场景

- 希望完全零介入、一键得到完美课堂笔记
- 希望在任何课程、任何平台上直接无适配使用
- 希望在 AI 字幕质量较差的情况下仍然稳定得到高质量结果

## 常见问题

**浏览器打开了但没反应？**
确认已在浏览器窗口完成南航统一认证登录，脚本会等页面加载完成后自动继续。

**提示 401 或登录失效？**
Cookie 过期了，重新跑 `python manage.py extract <课程名>` 会重新打开浏览器让你登录。

**只想用字幕不想用 Obsidian？**
完全没问题，`work/<teclId>/` 下的 transcript 文本独立可用，跳过 vault-init 和 sync 步骤即可。

**怎么支持第二门课？**
直接 `python manage.py add "<新的 video-detail URL>"` 即可，多门课共用一个 vault。
