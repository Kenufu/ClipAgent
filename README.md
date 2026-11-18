# ClipAgent

**COMP7608B · Group 59**

Gao Xuefei · Wang Ling · Zhang Yiqun · Fu Xuanyu

Submission documentation: [final report source](docs/FINAL_REPORT.md), [requirements checklist](docs/REQUIREMENTS_MATRIX.md), [architecture](docs/ARCHITECTURE.md), [work evidence](docs/WORK_LOG.md), [contribution confirmation](docs/CONTRIBUTIONS.md), and [AI assistance disclosure](docs/AI_USE_DECLARATION.md).

Academic diagrams: [six-page vector figure atlas](deliverables/ClipAgent_Academic_Figures.pdf), [16-slide editable academic deck](deliverables/ClipAgent_Academic.pptx), [Chinese explanation guide](docs/FIGURE_GUIDE.md), and [editable SVG sources](docs/figures/). The report now embeds architecture, state transitions, scoring, time mapping, bounded repair and evaluation-design figures directly.

The delivered controller is deterministic and uses pretrained Whisper for speech recognition. It does **not** include a generative LLM planner, LangGraph, MCP server, visual semantic reasoning, or cross-session preference memory. Thumbnail display is not visual understanding. No model training or fine-tuning was performed. These differences from the proposal are recorded in the report.

Local demo for evidence-grounded video editing. It accepts 1–3 MP4 files, transcribes English speech, selects source-linked clips for requested topics, exports an MP4 and SRT, and checks the finished file. The editor includes source monitoring, frame thumbnails, a zoomable timeline, manual clip insertion/splitting/trimming/reordering, and a live execution console. Follow-up instructions reuse cached source analysis.

The verification report lists each requested topic and the speech evidence still present in the final timeline. Manual trims trigger a fresh evidence check; missing topics remain flagged for review. The browser workbench keeps edits, preview, clip timeline, evidence, checks and activity in one responsive view.

## Run locally

Tested on Python 3.12 and macOS. The demo bundles FFmpeg through `imageio-ffmpeg`, so a system FFmpeg installation is not required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'from faster_whisper import WhisperModel; WhisperModel("tiny.en", device="cpu", compute_type="int8", download_root="data/models")'
.venv/bin/python -m scripts.prepare_samples
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>. Open **项目**, then choose **运行示例项目** for the prepared three-video demonstration, or upload English MP4 files with **新建项目**. The first model download requires internet access. `scripts.make_demo` uses the macOS `say` voice; uploading your own videos works on other systems. Public sample preparation and provenance are provided under `sample_data/`.

If the Python.org macOS installation reports a certificate error while installing packages or downloading the model, set `PIP_CERT=/etc/ssl/cert.pem` for pip and `SSL_CERT_FILE=/etc/ssl/cert.pem` for the model-download command.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app.py` | Local API and file upload |
| `clipagent/planning.py` | Request parsing, evidence selection, timeline and subtitle mapping |
| `clipagent/media.py` | Video inspection, transcription, rendering and decoding check |
| `clipagent/storage.py` | SQLite job records and activity history |
| `clipagent/service.py` | Stateful execution, revision and limited duration repair |
| `web/` | Editing workspace |
| `web/icons/` | Locally served Lucide icons and their license |
| `scripts/` | Reproducible sample media |
| `tests/` | Planning and media tests |
| `data/` | Local model weights, uploads, outputs and SQLite (ignored by Git) |

Run tests with `.venv/bin/python -m unittest discover -s tests -v`.

## Model, hardware, and data assumptions

- Speech recognition: `faster-whisper==1.2.1`, default `tiny.en`, CPU, int8, beam size 5, word timestamps, English, previous-text conditioning disabled.
- `CLIPAGENT_WHISPER_MODEL` overrides the model identifier. Download that model to `data/models` before running. Inference uses local files only.
- Runtime versions are pinned in `requirements.txt`. This application was tested on Python 3.12 / macOS. A discrete GPU, external database and paid API account are not required. Actual latency depends on CPU and input length.
- One background worker processes jobs serially. Inputs: 1–3 MP4 files, at most 15 minutes combined, at most 2 GB total. Output target: 1–600 seconds, 16:9 or 9:16, hard cuts and optional subtitles.
- Media and SQLite state remain under local `data/`. Model and sample downloads require internet access. No external inference API is called. The local app has no user authentication and should remain bound to `127.0.0.1`.
- A successful decode proves technical validity, not semantic correctness or editorial quality. Read `needs_review` warnings and inspect the output.

## Demonstration requests

1. Ordinary: `Create a 25-40 second recap covering the problem, solution, and demonstration result; export vertically.` Use the three generated sample videos.
2. Changed request: `Create a 10-20 second recap covering only solution; export horizontally.` Submit using the modification command bar. Cached transcription is reused.
3. Missing evidence: `Create a 20-30 second recap covering quantum teleportation; export vertically.` On the sample videos the missing topic should be reported, rather than labelled fulfilled.
4. Manual editing: select a timeline clip, edit its source in/out points, then choose **重新渲染**. The service reassesses retained speech evidence.

Use supported explicit English topic names and duration phrases for the evaluation. Chinese UI labels do not imply general Chinese instruction or speech understanding. Request interpretation uses a restricted set of patterns.

## Evaluation and submission

A real NASA-video walkthrough, reproducible browser checks, and downloadable output are documented in [the real video demo guide](docs/REAL_VIDEO_DEMO.md). The 61-second input is included under `sample_data/nasa/`; source attribution and preparation are explicit. The recording is an actual browser session with Chinese instructional captions, not a simulated product animation.

Watch the [recorded walkthrough](deliverables/demo/ClipAgent-real-demo.mp4), play the [actual exported result](deliverables/demo/NASA-edited.mp4), or read the [test results overview](docs/TEST_RESULTS.md). The application must be opened through its running local server, not by opening `web/index.html` as a file.

Evaluation scripts and their actual outputs live in `evaluation/`; its README documents commands, denominators, and limitations. Unit tests, curated transcript cases, real media checks, and the public speech sample are reported separately. Synthetic cases are not a held-out natural-video benchmark. The report includes unimplemented proposal items and pending human review.

Build a distributable source snapshot with:

```bash
.venv/bin/python -m scripts.package_submission
```

This writes `deliverables/Group59-ClipAgent-Submission.zip`. The ZIP includes a source manifest with SHA256 hashes and the base Git commit. It excludes local job databases, model weights, credentials, personal proposal files, virtual environments and caches. Submit the report PDF separately as required by the guideline. Presentation material is an additional demo aid.

The report PDF can be rebuilt using the optional `requirements-artifacts.txt` dependencies and `python -m scripts.build_report`. The presentation uses the Codex bundled `@oai/artifact-tool` environment; see `docs/ARTIFACT_BUILD.md`. It is an optional authoring dependency, not required by the runnable app. The PPTX itself is editable in ordinary presentation software.

Before submitting, all members must verify their actual contributions and AI usage in `docs/CONTRIBUTIONS.md` and `docs/AI_USE_DECLARATION.md`. Proposed responsibilities are not evidence of completed work. The prompt record is explicitly partial.

See [the implementation plan](docs/PLAN.md) for project milestones. This is a first working demo: lexical speech evidence is implemented; visual evidence, embedding retrieval, MCP wrapping, cross-session preference memory and broader benchmark evaluation remain future work. The original group proposal PDF is kept locally and excluded from Git because it includes personal information.
