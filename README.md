# ClipAgent

Local demo for evidence-grounded video editing. It accepts 1–3 MP4 files, transcribes English speech, selects source-linked clips for requested topics, exports an MP4 and SRT, and checks the finished file. The timeline can be edited and follow-up instructions reuse cached source analysis.

## Run locally

Requires Python 3.12 or newer on macOS. The demo bundles FFmpeg through `imageio-ffmpeg`, so a system FFmpeg installation is not required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'from faster_whisper import WhisperModel; WhisperModel("tiny.en", device="cpu", compute_type="int8", download_root="data/models")'
.venv/bin/python -m scripts.make_demo
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>. Choose **Run sample edit** for the prepared three-video demonstration, or upload your own English MP4 files. The first model download requires internet access. `scripts.make_demo` uses the macOS `say` voice; uploading your own videos works on other systems.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app.py` | Local API and file upload |
| `clipagent/planning.py` | Request parsing, evidence selection, timeline and subtitle mapping |
| `clipagent/media.py` | Video inspection, transcription, rendering and decoding check |
| `clipagent/storage.py` | SQLite job records and activity history |
| `clipagent/service.py` | Stateful execution, revision and limited duration repair |
| `web/` | Editing workspace |
| `scripts/` | Reproducible sample media |
| `tests/` | Planning and media tests |
| `data/` | Local model weights, uploads, outputs and SQLite (ignored by Git) |

Run tests with `.venv/bin/python -m unittest discover -s tests -v`.

See [the implementation plan](docs/PLAN.md) for project milestones. This is a first working demo: lexical speech evidence is implemented; visual evidence, embedding retrieval, MCP wrapping, cross-session preference memory and broader benchmark evaluation remain future work. The original group proposal PDF is kept locally and excluded from Git because it includes personal information.
