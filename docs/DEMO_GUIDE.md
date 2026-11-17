# Live demonstration and two-minute pitch

## Preparation

Use the README to install and cache tiny.en before demo day. Run the public sample script and the system checks. Start `uvicorn app:app --host 127.0.0.1 --port 8765` from the activated environment. Keep the public static-audio-wrapper MP4 and generated three-source sample available. Test the projector and native video playback. Every group member must attend the assigned session.

## Two-minute English pitch

“We built ClipAgent for students and presenters who need a short recap of English spoken material. The input is up to three MP4 files and a brief specifying topics, duration and orientation. The output includes a video, subtitles, an editable timeline and a verification report.

Our implemented agent uses pretrained speech recognition and a deterministic controller. It locates timestamped speech, selects clips, validates the timeline and invokes FFmpeg. After rendering it observes the actual output. It can remove optional content or add context when duration is wrong, with at most three render attempts. Missing evidence becomes a review warning. Tool failures stop the job and hide stale exports.

The interface lets a user inspect original footage, select and trim clips, reorder the timeline and revise a request while reusing the transcript. Our contribution includes this integrated workflow, evidence tracking, subtitle remapping, bounded recovery, API validation and a reproducible test harness.

On 18 synthetic cases, the full planner passes ten of fourteen feasible cases, compared with one for chronological selection. This is a component result, not a claim about natural-video editing quality. A separate public speech example exercises real transcription and rendering. We also retain failures involving negation and merged-clip ordering.

We will now run a brief, inspect its evidence and checks, change the request, and show how the system reports a missing topic.”

## Live sequence

1. Show the source bin and identify whether using generated demo sources or the public static wrapper.
2. Run a supported English brief, watch phase events, inspect MP4/SRT/timeline/report.
3. Request portrait instead of landscape, or only a named topic. Show cached transcript reuse.
4. Trim a clip in Properties, render again, inspect updated evidence.
5. Require an absent topic such as quantum teleportation and show `needs_review`.
6. Explain one retained injected render/decode failure trace, explicitly naming it as fault injection.

If the model cache is missing, fix it before the session. Prepared outputs can illustrate artifacts but cannot replace the required live interactive demo. Allow the teaching team to choose within the stated supported scope.

## Q&A preparation

- Why no training? The prototype reuses pretrained ASR; a benchmark is needed before justifying learned planning.
- What is autonomous? Evidence choice, context assembly, tool execution, observation-dependent repair and bounded stopping.
- What remains limited? Lexical semantics, original visual content, natural instructions, human quality evaluation and restart recovery.
- Is the report circular? Technical checks are separate from developer-authored acceptable intervals, but independent human annotation is still missing.
- What is the actual workload? Explain concrete modules, tests, failure fixes and Git milestones from WORK_LOG, without inventing personal hours.
- How does this differ from the proposal? Clearly disclose the missing LLM/VLM/MCP/memory components and smaller evaluation set.
