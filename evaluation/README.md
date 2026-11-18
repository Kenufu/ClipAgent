# Evaluation reproduction

From the repository root with application dependencies installed:

```sh
.venv/bin/python -m evaluation.run --repeats 20 --output evaluation/results
.venv/bin/python scripts/run_system_checks.py
.venv/bin/python scripts/run_public_sample.py
.venv/bin/python -m unittest discover -s tests -v
```

`results/`: 18 developer-authored synthetic transcript cases, three planning methods, independent interval/constraint scoring, 54 per-method traces. Four cases are deliberately infeasible. Coverage includes all requirements; feasible pass rate uses the 14 feasible cases. Duration observations are simulated. The chronological baseline shares the parser/inputs, selects early speech and has no topic ranking. The planner and repair variant use the same evidence selection. This is not the proposed LLM baseline and does not establish real-video performance.

`system_results/`: real in-process HTTP/SQLite/worker/media operations and explicitly labelled injected faults. These include invalid media, missing speech, manual changes, revision, queue failure, render failure, decode rejection and a three-render limit. Speech tests require existing local model files and skip when unavailable. Local macOS speech synthesis may return empty audio and is separately skipped; the public WAV test covers real ASR when cached weights exist.

`public_results/`: one CC BY 4.0 speech sample wrapped in a synthetic title card, real ASR/planning/render/decode with wall time. No independent human score or complete-reference WER is claimed. Do not combine this sample with synthetic cases into an end-to-end accuracy percentage.

`browser_results/`: actual Chrome UI operations on a real NASA video excerpt using the local backend and cached Whisper model. Includes upload and job-opening regression, timeline controls, revision/cache reuse, export, missing evidence, project drawer state, three viewport sizes, video element bounds and HTTP Range checks. See `docs/REAL_VIDEO_DEMO.md` to reproduce the recording. Screenshots, sanitized job snapshots, network responses and a separate assertion summary are included. The source/topic choices are curated; this is workflow verification, not a held-out semantic accuracy score. Automatic subtitle errors are retained.

Cases and expected intervals are authored during development, not a held-out benchmark. Negation, synonym and merged-clip order failures remain in the results. An identified repair ordering bug was fixed and regression-tested. Synthetic observed duration offsets deliberately exercise repair; they are not measured encoder drift.

No paid inference service or LLM judge is used. Results contain source hashes, model/environment settings where applicable, denominators and per-case evidence. Run timings vary with hardware/cache load. Human assessment is still required before making subjective editing-quality claims.
