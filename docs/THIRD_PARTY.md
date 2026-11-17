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

Synthetic evaluation transcripts and interval labels were authored during AI-assisted development. Demo narration scripts are project-created and rendered through macOS speech synthesis; these are not consented participant recordings. No externally authored video benchmark or human evaluation dataset is claimed. The included demo MP4s come from scripts/make_demo.py and use generated title cards and system speech.
