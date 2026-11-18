# Sources and attribution

The project integrates existing tools rather than implementing their model training or codec internals. Retain their upstream notices when redistributing those packages; the submission includes requirements, not installed dependencies or model weights.

| Source | Use and attribution location |
| --- | --- |
| https://github.com/SYSTRAN/faster-whisper | Pretrained speech inference wrapper; model downloaded separately |
| https://huggingface.co/Systran/faster-whisper-tiny.en | Default converted Whisper model; exact cached revision in public_results/results.json |
| https://github.com/openai/whisper | Original pretrained Whisper model family |
| https://ffmpeg.org/ | Media encoding, decoding, subtitles and thumbnails via imageio-ffmpeg |
| https://github.com/imageio/imageio-ffmpeg | Bundled executable distribution |
| https://pyav.org/ | Container and stream inspection |
| https://fastapi.tiangolo.com/ | Local HTTP application |
| https://www.uvicorn.org/ | Application server |
| https://www.sqlite.org/ | Local job/event persistence through Python sqlite3 |
| https://lucide.dev/ | Icons; license preserved in web/icons/LICENSE |
| https://www.openslr.org/12/ | LibriSpeech sample; creators, CC BY 4.0 text and redistribution provenance in sample_data |
| Codex bundled artifact tooling and ReportLab | Optional deck/report authoring, separate from runtime app |
| https://www.nasa.gov/nasa-brand-center/images-and-media/ | Real interview excerpt for educational demonstration; exact source and hashes in sample_data/nasa/provenance.json |
| https://playwright.dev/python/ | Optional real-browser assertions and recording; installed separately through requirements-browser.txt |

Synthetic evaluation transcripts and interval labels were authored during AI-assisted development. The three generated MP4s in sample_data/demo come from scripts/make_demo.py, using project narration, title cards and macOS speech synthesis. The separate sample_data/nasa clip is real public NASA footage, prepared and attributed as described in its README. Neither is a held-out video benchmark or a human evaluation dataset.
