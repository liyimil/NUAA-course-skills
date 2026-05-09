# 安装说明

## 1. 安装 Python 依赖

```powershell
cd skills\nuaa-vod-summarizer
python -m pip install -r requirements.txt
python -m playwright install chromium
```

如果你希望优先使用 Edge 或 Chrome，只要本机已安装对应浏览器即可。脚本默认尝试 `msedge`。

## 2. 首次运行

```powershell
python scripts\extract_nuaa_vod.py "https://ft.nuaa.edu.cn/jy-application-vod-he-ui/#/video-detail?id=118467" --output-dir ".\work\118467" --browser-runtime-auth --manual-wait-seconds 180
```

`--browser-runtime-auth` 会打开一个可见浏览器窗口。首次使用时，请在窗口里完成南航登录；脚本会等待 `--manual-wait-seconds` 指定的时间后继续。

## 3. 输出文件

典型输出：

```text
work/
  118467/
    raw/
      page.json
      captured_responses.json
      replay_inventory.json
      storage_state.json
      responses/
      transcript.txt
    semantic_rebuild/
      semantic_rebuild_input.json
      semantic_rebuild_prompt.md
```

如果没有捕获到字幕响应，则不会生成正式 transcript。

## 4. 注意事项

- 南航 VOD 接口需要登录态，裸请求会返回 `401`。
- 第一版脚本先保留真实接口响应，字段解析会随着样本继续收敛。
- 不要只凭课件或视频元信息生成正式课堂笔记；正式笔记必须以字幕/转写为主要来源。
