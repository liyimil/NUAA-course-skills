# NUAA Course Skills

把南航飞天云课堂的课程点播、AI 字幕、课件和课次元信息，整理成可继续语义重建的课程学习资料，支持接入 Obsidian 长期知识库维护。

**多课程支持**：通过 `manage.py` 统一管理所有课程，添加新课程只需一行命令。

## 快速开始

```powershell
# 1. 安装依赖
cd skills\nuaa-vod-summarizer
python -m pip install -r requirements.txt
python -m playwright install chromium

# 2. 初始化 Obsidian vault（一次性）
cd ..\..
python manage.py vault-init
```

## 日常使用

### 添加新课程

打开南航飞天云课堂，找到课程的 `video-detail` 链接，然后：

```powershell
python manage.py add "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=118467"
```

浏览器会打开等待登录。脚本自动完成：
- 枚举全部课次
- 识别有 AI 字幕的课次
- 批量拉取字幕
- 注册到课程表

后续再次抽取（cookie 有效时）：

```powershell
python manage.py extract 操作系统 --skip-existing
```

### 查看状态

```powershell
python manage.py list          # 所有课程一览
python manage.py status 操作系统  # 单门课详情
```

输出示例：

```
Course           teclId     Finished   Pending    Vault
操作系统           118467     3          19         yes
计算机网络          120345     1          31         yes
```

### 生成笔记

每门课的抽取数据在 `work/<teclId>/` 下，每个课次独立目录下有 `transcript.txt`。由 Claude/Codex 读取 transcript 生成 `note.md`。

### 同步到 Obsidian

写完笔记后：

```powershell
python manage.py sync 操作系统        # 同步单门课
python manage.py vault-sync-all       # 同步全部课程
```

同步会自动更新 vault 中的：
- `00-课程总览.md` — 课程元信息 + 课次索引
- `已整理课次.md` — 已完成笔记一览
- `待整理回放.md` — 还在排队等写笔记的课次
- `事务.md` — 作业/考试/通知汇总
- `课次/<日期> <课程> 第N节.md` — 笔记文件

## 添加第二门课

只需要新的 `video-detail` URL：

```powershell
python manage.py add "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=XXXXX"
python manage.py extract 计算机网络 --skip-existing  # 后续批量抽取
# ... 写笔记 ...
python manage.py sync 计算机网络
```

## 项目结构

```
nuaa/
  manage.py                    # 多课程管理入口
  courses.json                 # 课程注册表
  work/<teclId>/               # 每门课的 VOD 抽取数据
  vault/                       # Obsidian vault（默认位置）
  skills/
    nuaa-vod-summarizer/       # VOD 抽取 skill
    obsidian-course-vault/     # Obsidian 课程库 skill
```

## Vault 结构

```
vault/
  00-Home.md
  01-Courses/
    操作系统/
      00-课程总览.md
      已整理课次.md / 待整理回放.md / 待回看问题.md
      事务.md / 章节完成度.md / 回放同步.md
      课次/
  02-Concepts/
  03-Admin/（作业总表、考试与通知）
```
