# ClipAgent demo plan

The submitted proposal defines the target: 1–3 English lecture, interview, or software-demo MP4 files (5–15 minutes total) become a source-linked recap, SRT, editable JSON timeline, and verification report. This repository begins with a smaller local demo and grows toward that target.

## Milestones

1. **Reliable media path:** accept MP4, inspect streams, transcribe speech, create an editable timeline, render MP4/SRT, and fully decode the result.
2. **Evidence-grounded planning:** rank timestamped speech against requested topics; inspect sampled frames only for visual requests; validate constraints before rendering.
3. **State and recovery:** persist job state and timeline revisions, support follow-up instructions, and apply bounded, check-specific repair.
4. **Evaluation:** prepare consented development and held-out recordings, compare rule-based, one-pass, and full-agent systems, and measure content coverage, output validity, latency, and cost.

## Local architecture

`web/` is the interface; `app.py` is the API; `clipagent/` contains state, planning, media execution, and verification; `scripts/` generates demo material; `tests/` checks planning and rendering. `data/` contains local videos, model weights, and SQLite and is deliberately excluded from Git.

The local demo uses CPU transcription and a bundled FFmpeg binary. No discrete GPU or external database is required. The first version keeps job records in SQLite and media files on disk. A later multi-user deployment can move state to PostgreSQL and assets to object storage without changing the timeline format.

## First-demo acceptance criteria

- Upload up to three MP4 files or run the prepared sample.
- Enter a brief with required topics, target duration, and aspect ratio.
- Inspect timestamped evidence and edit the selected clips.
- Download an MP4 and SRT with a report of checks and unresolved requirements.
- Revise the brief without retranscribing the source.

The current planner uses lexical evidence ranking and speech-based boundaries. Visual grounding, embedding retrieval, MCP wrapping, preference memory, and advanced repair remain subsequent milestones. The report must not label unresolved requirements as completed.
