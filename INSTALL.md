# 安装说明

## 环境要求

- Python 3.10+
- Windows / macOS / Linux
- 南航统一认证账号

## 安装步骤

### 1. 克隆仓库

```powershell
git clone https://github.com/liyimil/NUAA-course-skills.git
cd NUAA-course-skills
```

### 2. 创建课程表

```powershell
copy courses.example.json courses.json
```

### 3. 安装 Python 依赖

```powershell
cd skills\nuaa-vod-summarizer
python -m pip install -r requirements.txt
```

### 4. 安装浏览器

```powershell
python -m playwright install chromium
```

如果你已安装 Chrome 或 Edge，可以跳过此步。脚本默认优先使用 Edge（`msedge`），Chromium 作为后备。

### 5. （可选）初始化 Obsidian vault

```powershell
cd ..\..
python manage.py vault-init
```

这会创建 `vault/` 目录，用 Obsidian 打开该目录即可。

## 验证安装

```powershell
python manage.py list
```

如果看到空表格（或已有课程），说明安装成功。

## 首次添加课程

```powershell
python manage.py add "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=<你的课程ID>"
```

浏览器会打开，在窗口中完成南航登录即可，后续无需手动操作。

## 输出文件

抽取完成后，每门课的数据在 `work/<teclId>/` 下：

```
work/118467/
  course.json                        # 课程元信息
  replay_inventory.json              # 课次清单
  lessons/
    1547370/                         # 课次 ID
      metadata.json                  #   课次元信息
      note.md                        #   生成的笔记（手动/AI 生成）
      raw/                           #   原始 API 响应
      semantic_rebuild/              #   结构化输入（供 AI 读取）
```

## 注意事项

- 南航 VOD 接口需要登录态，Cookie 过期后重新运行会自动提示登录
- 不要只凭课件或视频元信息生成课堂笔记，正式笔记应以字幕/转写为主要来源
- `work/` 和 `vault/` 已在 `.gitignore` 中排除，不会被提交到 Git
