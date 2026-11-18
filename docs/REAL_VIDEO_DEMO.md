# 真实视频操作演示

## 文件与观看方式

- `deliverables/demo/ClipAgent-real-demo.mp4`：真实浏览器操作录屏，下方加中文步骤说明，末尾附完整剪辑成片及原声。
- `deliverables/demo/NASA-edited.mp4`：通过界面导出按钮下载的成片，可单独播放。
- `deliverables/demo/NASA-edited.srt`：通过界面下载的字幕文件。
- `sample_data/nasa/astronaut-training.mp4`：可直接上传复现的61秒真人视频素材。
- `evaluation/browser_results/`：操作断言结果、任务快照、网络响应记录及桌面/手机截图。

录屏由自动化浏览器操作真实页面生成，等待处理的时间保留。黄色圆圈仅用于显示鼠标位置。中文步骤说明是录制后加在界面外的解说字幕，不是产品功能。操作录屏段没有采集浏览器音频；末尾附的成片保留真实原声。

## 素材来源

NASA官方视频《#AskNASA – How Can I Be An Astronaut?》，原片约3分53秒。演示作者事先取其中113–174秒的训练问答片段，生成61秒输入素材。该准备步骤不归功于Agent。来源、使用说明、原片与片段的哈希值见 `sample_data/nasa/provenance.json` 和同目录README。此例是用于讲解的精选样例，不代表对任意真实视频的效果保证。

## 按视频复现

1. 启动本地应用，打开“项目 → 新建项目”，选择上述MP4素材。
2. 输入 `Create a 20-30 second recap covering training and spacewalks; export landscape with subtitles.`；必要主题填 `training, spacewalks`，目标25秒，画幅16:9。
3. 创建项目，查看顶部进度及右侧“控制台”。完成后切换“原素材 / 成片”，查看“证据”和“检查”。
4. 点击时间线上的片段、点击时间尺定位，使用剪刀分割。在“属性”中调整源入点，移动片段，再点击“重新渲染”。
5. 在下方修改指令栏输入 `Create a 15-25 second recap covering only spacewalks; export landscape.`。检查器验证必要主题，控制台记录复用转录。此处“only”更改的是必要主题，当前算法仍会添加上下文补足时长，不能保证排除其他内容。
6. 点击顶部“导出”下载MP4，点击“SRT”下载字幕。
7. 输入 `Create a 15-25 second recap covering quantum teleportation; export landscape.`，观察“待检查”和缺失主题；然后恢复第5步的指令。

## 自动录制与验证

先按根目录README安装应用和缓存Whisper模型，再安装可选依赖：

```bash
.venv/bin/python -m pip install -r requirements-browser.txt
.venv/bin/python -m playwright install ffmpeg
```

需要已安装Google Chrome。下面第一条命令在独立终端保持运行，使用独立的本地任务数据库，不修改原来的项目记录：

```bash
.venv/bin/python -m scripts.record_browser_demo --serve
```

另一个终端运行：

```bash
.venv/bin/python -m scripts.record_browser_demo
.venv/bin/python -m scripts.build_demo_video
```

中文解说字幕默认使用macOS自带黑体；其他系统需通过 `CLIPAGENT_DEMO_FONT` 指向支持中文的字体。字体文件不会随项目重新分发。视频导出完成后再运行字幕合成，避免同时写入同一成片。

演示服务地址为 `http://127.0.0.1:8770`。录制会创建一个新项目；脚本不拦截API、不注入转录、不伪造进度或检查结果。测试包含真实上传、新任务打开、分割、属性裁剪、移动并恢复、重新渲染、指令修改、缓存复用、缺失主题、下载、抽屉持久化、Esc关闭、桌面和手机布局以及视频Range请求。

既有27项单元/媒体测试通过 `.venv/bin/python scripts/run_all_tests.py` 运行；它们与浏览器断言分别记录，避免混算测试数量。录制脚本读取接口数据仅用于断言和保存证据，所有剪辑操作通过页面完成。

## 本次修复

真实上传流程的检查发现：表单提交处理在等待上传完成后再读取 `event.currentTarget`，这时该值已清空，导致项目已创建但页面未打开。现在在等待前保存表单引用。录屏脚本从上传到打开新项目的断言覆盖了这条回归路径。

回看录屏发现监看器中的视频元素会按自身宽高比撑高，超出分配的区域，裁掉下方画面和控件。现在将视频约束在监看器容器内，保留完整画面；三个窗口尺寸均验证视频元素和容器尺寸一致。

自动字幕保留系统的实际输出，未人工改写。小型英文转录模型会错认专业名词，剪辑边界也可能带入相邻词，需要人复核；通过媒体检查不等于语义或字幕完全正确。
