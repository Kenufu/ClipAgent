from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import JOBS
from .media import render, transcribe, verify
from .planning import build_timeline, make_srt, parse_request, repair_duration, review_timeline_evidence, srt_max_end, validate_timeline
from .storage import event, get_job, update_job

_workers = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clipagent")


def submit(job_id, *, revision=False, manual_timeline=None):
    _workers.submit(_process, job_id, revision, manual_timeline)


def _process(job_id, revision, manual_timeline):
    try:
        job = get_job(job_id)
        assets = job["assets"]
        options = parse_request(job["instruction"], job["options"])
        update_job(job_id, status="running", options=options, error=None)

        if revision:
            transcript = job["transcript"]
            event(job_id, "replanning", "Reusing cached transcript for the revision")
        else:
            transcript = []
            event(job_id, "transcribing", "Transcribing spoken evidence")
            for asset in assets:
                if asset["has_audio"]:
                    transcript.extend(transcribe(asset["path"], asset["id"]))
                event(job_id, "transcribing", f"Analyzed {asset['name']}")
            update_job(job_id, transcript=transcript)

        event(job_id, "planning", "Selecting source-linked clips")
        if manual_timeline is not None:
            timeline, _, _ = review_timeline_evidence(
                manual_timeline, transcript, options["topics"], annotate=True
            )
            unresolved = []
        else:
            timeline, unresolved = build_timeline(assets, transcript, options)
        predicted = validate_timeline(timeline, assets)
        version = job["version"] + 1
        update_job(job_id, timeline=timeline, version=version)
        output_dir = JOBS / job_id / "output"
        repairs = []
        for attempt in range(3):
            event(job_id, "rendering", f"Rendering timeline version {version}")
            srt = make_srt(timeline, transcript) if options["subtitles"] else ""
            final, captions = render(assets, timeline, srt, options["aspect"], output_dir)
            event(job_id, "verifying", "Decoding and checking the finished video")
            checks = verify(final, options["aspect"])
            if manual_timeline is not None or attempt == 2:
                break
            revised, reason = repair_duration(timeline, transcript, assets, options, checks["duration"])
            if revised is None:
                break
            validate_timeline(revised, assets)
            repairs.append(reason)
            event(job_id, "repairing", reason)
            timeline = revised
            predicted = validate_timeline(timeline, assets)
            version += 1
            update_job(job_id, timeline=timeline, version=version)

        _, topic_evidence, missing_topics = review_timeline_evidence(
            timeline, transcript, options["topics"]
        )
        unresolved = [
            issue for issue in unresolved
            if not issue.startswith("No reliable spoken evidence found for:")
        ]
        unresolved.extend(issue for issue in missing_topics if issue not in unresolved)
        checks["predicted_duration"] = predicted
        checks["subtitle_cues"] = srt.count(" --> ")
        checks["subtitle_within_video"] = srt_max_end(srt) <= checks["duration"] + 0.05
        checks["duration_ok"] = (
            options["min_seconds"] - 0.7 <= checks["duration"] <= options["max_seconds"] + 0.7
        )
        if checks["duration_ok"]:
            unresolved = [issue for issue in unresolved if "duration" not in issue.lower()]
        elif not any("duration" in issue.lower() for issue in unresolved):
            unresolved.append("Rendered duration is outside the requested range")
        if not checks["aspect_ok"]:
            unresolved.append("Rendered aspect ratio is incorrect")
        if not checks["has_audio"]:
            unresolved.append("Output has no audio stream")
        if not checks["subtitle_within_video"]:
            unresolved.append("Subtitle timing exceeds the rendered duration")
        status = "needs_review" if unresolved else "complete"
        report = {
            "unresolved": unresolved,
            "checks": checks,
            "evidence_count": len(transcript),
            "topic_evidence": topic_evidence,
            "timeline_version": version,
            "repairs": repairs,
            "outputs": {"video": final.name, "subtitles": captions.name},
        }
        update_job(job_id, status=status, report=report)
        event(job_id, status, "Export verified" if status == "complete" else "Export needs review")
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc))
        event(job_id, "failed", str(exc))
