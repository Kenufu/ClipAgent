# ClipAgent · 有来源依据的视频剪辑工作台

**COMP7608B · Group 59**　|　[English README](README_EN.md)

成员：Gao Xuefei · Wang Ling · Zhang Yiqun · Fu Xuanyu

上传英文视频、描述剪辑要求，ClipAgent 会转录语音、选择相关片段、生成视频和字幕，并检查输出文件。你可以在时间线上分割、裁剪、排序，再重新渲染；右侧可查看语音证据、检查结果和执行日志。

**无需独立显卡、外部数据库或付费 API。** 当前版本使用预训练 Whisper 和确定性规则规划，没有训练新模型，也尚未实现生成式 LLM 规划、视觉语义理解或长期偏好记忆。

## 先看真实演示

| 内容 | 入口 |
| --- | --- |
| 约 2 分 08 秒的完整操作演示，带中文步骤说明，末尾附原声成片 | [观看／下载演示视频](https://github.com/Kenufu/ClipAgent/raw/refs/heads/main/deliverables/demo/ClipAgent-real-demo.mp4) |
| 系统实际导出的约 16.7 秒成片 | [下载成片 MP4](https://github.com/Kenufu/ClipAgent/raw/refs/heads/main/deliverables/demo/NASA-edited.mp4) · [字幕 SRT](deliverables/demo/NASA-edited.srt) |
| 自己动手复现的 61 秒 NASA 真人视频节选 | [源素材](sample_data/nasa/astronaut-training.mp4) · [来源与使用说明](sample_data/nasa/README.md) |
| 演示步骤与可复制的指令 | [中文使用指南](docs/REAL_VIDEO_DEMO.md) |

视频记录真实浏览器上传、自动处理、手动修改、缺失主题提示和导出，未替换后端结果。操作录屏段没有旁白，末尾成片保留原声。自动字幕未人工修正，可能有专业词识别错误。GitHub 如未显示播放器，可下载后播放。

## Mac 快速安装与启动

### 1. 下载安装包

**[下载 macOS 快速启动包 ZIP](https://github.com/Kenufu/ClipAgent/raw/refs/heads/main/downloads/ClipAgent-macOS-Quickstart.zip)**　|　[SHA256 校验值](downloads/ClipAgent-macOS-Quickstart.zip.sha256)

包内包含代码、示例素材、演示视频和课程材料。它是自动配置环境的源码安装包，**不是已签名的 `.dmg/.app`，也不包含 Python 运行时或模型权重**。

### 2. 首次安装

1. 先安装 **Python 3.12**：可从 [Python 官方 Mac 下载页](https://www.python.org/downloads/macos/)选择对应版本。当前主要在 Apple Silicon Mac、Python 3.12 上验证，其他平台尚未完整验证。
2. 解压 ZIP，把整个 `ClipAgent` 文件夹放在你准备长期保存项目的位置。
3. 双击 **`安装 ClipAgent.command`**。它会创建项目独立环境、安装依赖、下载 Whisper `tiny.en`，并准备演示素材。首次需要网络，耗时取决于下载速度。
4. 看到“安装完成”后，双击 **`启动 ClipAgent.command`**。工作台就绪后会自动打开浏览器。

如果系统要求确认打开脚本，可右键文件选择“打开”。也可以在解压目录的终端执行：

```bash
bash '安装 ClipAgent.command'
bash '启动 ClipAgent.command'
```

### 3. 以后直接启动

只需双击 **`启动 ClipAgent.command`**。默认从 `http://127.0.0.1:8765` 启动；端口被占用时会选择附近空闲端口，以终端显示的地址为准。**保持终端窗口打开，按 Ctrl+C 停止服务。**

完整功能需要本地服务，请访问启动后显示的网址。直接打开 `web/index.html` 文件不能运行后端剪辑功能。

模型缓存和依赖就绪后，剪辑推理在本机进行。安装失败可联网后重新运行安装脚本；它会优先使用已缓存模型，不要求删除项目数据。

## 第一个剪辑任务

打开“项目 → 新建项目”，上传 `sample_data/nasa/astronaut-training.mp4`：

- 剪辑要求：`Create a 20-30 second recap covering training and spacewalks; export landscape with subtitles.`
- 必须包含的主题：`training, spacewalks`
- 目标时长：`25` 秒；画幅：`16:9`。

点击创建后，在“控制台”查看过程。完成后查看“证据”和“检查”，再播放成片。选择时间线片段后可编辑入点、出点，或使用剪刀分割，修改后点击“重新渲染”。

修改指令示例：`Create a 15-25 second recap covering only spacewalks; export landscape.`

这里的 `only` 修改必要主题，当前规则仍可能加入上下文补足时长，不保证排除其他内容。界面虽为中文，语音识别和指令解释主要按英文样例验证，不代表支持任意中文需求。

也可以在“项目”抽屉点击“运行示例项目”，使用包内三个合成示例视频。

## 支持范围与运行方式

| 项目 | 当前实现 |
| --- | --- |
| 输入 | 1–3 个 MP4，总时长不超过 15 分钟，总文件大小不超过 2 GiB |
| 输出 | MP4、SRT、时间线 JSON、验证报告 JSON；横屏 16:9 或竖屏 9:16 |
| 操作 | 素材预览、缩略帧、时间线缩放、添加、分割、裁剪、排序、修改指令 |
| 语音模型 | faster-whisper / tiny.en，CPU INT8；预训练模型推理，没有微调 |
| 规划与验证 | 词汇证据选择、来源时间戳映射、FFmpeg 渲染、解码与时长等检查；自动时间线最多三次渲染 |
| 数据 | SQLite 与本地文件；任务、上传、输出和模型缓存位于 `data/` |

本机工作台没有用户登录和多用户权限控制，启动脚本只绑定 `127.0.0.1`。上传内容和转录不会因关掉页面而自动删除。视频可解码不等于剪辑语义正确，需要查看 `needs_review` 提示并人工复核。

## 测试与评估

- 已记录的单元／媒体测试：**26 项通过、1 项跳过、无失败**。跳过项是当前环境无法产生音频的 macOS 合成语音测试。
- 真实 NASA 素材浏览器验证：**9 组检查通过**，覆盖上传、手动编辑、修改指令、导出、缺失主题、抽屉状态、桌面／手机布局和视频 Range 请求。
- 规划评估：18 个开发者编写的案例、3 种方法、54 条记录；规划加修复在 14 个可行案例中通过 10 个。它不是独立真实视频基准，也不是人工质量评分。

[完整测试说明](docs/TEST_RESULTS.md) · [浏览器验证记录](evaluation/browser_results/summary.json) · [评估复现说明](evaluation/README.md)

快速启动包另已通过独立目录安装、环境检查、端口冲突回退、页面／健康接口和关闭服务验证，详见 [安装包验证记录](docs/QUICKSTART_VERIFICATION.md)。

```bash
.venv/bin/python scripts/run_all_tests.py
.venv/bin/python -m evaluation.run --repeats 20 --output evaluation/results
```

## 架构、原理图与汇报材料

| 材料 | 文件 |
| --- | --- |
| 系统架构、状态机、评分公式、时间映射、修复机制、实验设计 | [六页学术图册](deliverables/ClipAgent_Academic_Figures.pdf) |
| 16 页可编辑演示稿 | [学术版 PPT](deliverables/ClipAgent_Academic.pptx) |
| 含矢量图的报告 | [报告 PDF](deliverables/Group59-ClipAgent-Final-Report.pdf) · [Markdown 源文档](docs/FINAL_REPORT.md) |
| 图解答辩讲法 | [中文讲解稿](docs/FIGURE_GUIDE.md) · [SVG 图源](docs/figures/) |
| 课程要求、工作记录与披露 | [要求对照](docs/REQUIREMENTS_MATRIX.md) · [工作记录](docs/WORK_LOG.md) · [成员分工](docs/CONTRIBUTIONS.md) · [AI 使用说明](docs/AI_USE_DECLARATION.md) |

实际成员分工待团队核实。原 proposal 中的 LLM／多模态规划、LangGraph／MCP、长期偏好记忆和更大规模数据集未全部实现，报告已记录范围差异。

## 项目结构

```text
app.py                   本地接口与上传校验
clipagent/               规划、媒体工具、执行控制、状态存储
web/                     深色剪辑工作台与本地托管图标
scripts/                 安装准备、启动、测试、素材与文档构建
sample_data/             可复现素材及来源说明
tests/ + evaluation/     测试与实际评估记录
docs/                    架构、报告、图源、使用与答辩说明
deliverables/            报告、PPT、真实演示视频
downloads/               macOS 快速启动包
data/                    本地运行数据，不上传 GitHub
```

## 手动安装与常见问题

开发者可按 [英文说明](README_EN.md)手动创建环境、安装依赖并启动 Uvicorn；文档构建依赖另见 [构建说明](docs/ARTIFACT_BUILD.md)。FFmpeg 随依赖提供，无需另装数据库或购买 API。

- **端口被占用**：启动脚本会自动换端口；使用它输出的新地址。
- **模型缺失／下载失败**：检查网络后重跑安装；正常启动不会悄悄联网下载模型。
- **证书错误**：Mac 安装脚本在存在时使用系统证书文件，并尊重已有证书环境设置，不关闭证书验证。
- **关闭终端后网页不能使用**：服务已停止，再运行启动脚本。
- **想恢复安装**：优先在新解压目录安装；保留原目录中的 `data/`，避免丢失自己的项目。

NASA 和 LibriSpeech 素材的来源及使用条件保留在各自的 `sample_data/` 目录；软件依赖与图标归属见 [第三方说明](docs/THIRD_PARTY.md)。
