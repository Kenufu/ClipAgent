# ClipAgent demo plan

The submitted proposal defines the target: 1–3 English lecture, interview, or software-demo MP4 files (5–15 minutes total) become a source-linked recap, SRT, editable JSON timeline, and verification report. This repository begins with a smaller local demo and grows toward that target.

## Milestones

1. **Reliable media path — complete:** accept MP4, inspect streams, transcribe speech, create an editable timeline, render MP4/SRT, and fully decode the result.
2. **Editor workbench — complete:** preview source media and output, inspect source thumbnails, scrub and zoom the timeline, add/split/trim/reorder clips, and watch live execution events.
3. **Evidence-grounded planning — in progress:** rank timestamped speech against requested topics, add visual evidence from sampled frames, and validate constraints before rendering.
4. **Evaluation dataset — next:** prepare 30–50 consented editing jobs with a brief, source pack, reference timeline, reference export, and human scores.
5. **Model experiment — gated by evaluation:** compare rules, retrieval, a prompted visual-language model, and LoRA only when the benchmark shows a repeatable gap.
6. **State and recovery:** retain timeline versions, support undo/redo and resumable jobs, and apply bounded, check-specific repair.

## How to use this plan

Every milestone must end with a runnable demo, tests, and one Git commit. Do not start training from the availability of data alone. First run the current baseline on the evaluation set, record failures by category, and train only if prompt, retrieval, and rule changes do not close the gap.

The immediate development sequence is:

1. Finish visual evidence extraction and link each selected clip to speech or frame evidence.
2. Add a `datasets/clipagent-benchmark` manifest and annotation workflow for 30–50 jobs.
3. Add automatic metrics for topic coverage, duration, aspect ratio, decode success, and timeline overlap, plus a human rhythm and quality score.
4. Run the baseline and publish an error analysis.
5. Decide whether a small planner LoRA is justified; keep Whisper and the visual encoder pretrained unless the evaluation isolates a specific failure.

## Local architecture

`web/` is the interface; `app.py` is the API; `clipagent/` contains state, planning, media execution, and verification; `scripts/` generates demo material; `tests/` checks planning and rendering. `data/` contains local videos, model weights, and SQLite and is deliberately excluded from Git.

The local demo uses CPU transcription and a bundled FFmpeg binary. No discrete GPU or external database is required. The first version keeps job records in SQLite and media files on disk. A later multi-user deployment can move state to PostgreSQL and assets to object storage without changing the timeline format.

## First-demo acceptance criteria

- Upload up to three MP4 files or run the prepared sample.
- Enter a brief with required topics, target duration, and aspect ratio.
- Inspect timestamped evidence and edit the selected clips.
- Preview raw source media, add or split clips, and observe the execution log.
- Download an MP4 and SRT with a report of checks and unresolved requirements.
- Revise the brief without retranscribing the source.

The current planner uses lexical evidence ranking and speech-based boundaries. Visual grounding, embedding retrieval, MCP wrapping, preference memory, and advanced repair remain subsequent milestones. The report must not label unresolved requirements as completed.
