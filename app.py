import re
import shutil
import uuid
from pathlib import Path
from threading import RLock
from functools import wraps

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from clipagent.config import DEMO, JOBS, MAX_FILES, MAX_TOTAL_SECONDS, MAX_UPLOAD_BYTES, ROOT
from clipagent.media import preview_frame, probe
from clipagent.planning import validate_timeline
from clipagent.service import submit
from clipagent.storage import create_job, get_job, init_db, list_jobs, update_job
from clipagent.storage import event

init_db()
app = FastAPI(title="ClipAgent", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
_revision_lock = RLock()


def _serialized_revision(function):
    # Serialize the ready-check and queued transition across request threads.
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _revision_lock:
            return function(*args, **kwargs)
    return wrapped


def _submit(job_id, **kwargs):
    try:
        submit(job_id, **kwargs)
    except Exception as exc:
        update_job(job_id, status="failed", report={}, error=str(exc))
        event(job_id, "failed", f"Could not queue processing: {exc}")
        raise HTTPException(503, "Could not queue processing") from exc


class Revision(BaseModel):
    instruction: str = Field(min_length=3, max_length=3000)
    target_seconds: int | None = Field(default=None, ge=1, le=600)
    aspect: str | None = None
    topics: list[str] | None = None


class ClipEdit(BaseModel):
    asset_id: str
    start: float = Field(allow_inf_nan=False)
    end: float = Field(allow_inf_nan=False)


class TimelineEdit(BaseModel):
    clips: list[ClipEdit] = Field(min_length=1, max_length=100)


def _get(job_id):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


def _asset(job_id, asset_id):
    record = _get(job_id)
    asset = next((item for item in record["assets"] if item["id"] == asset_id), None)
    if asset is None or not Path(asset["path"]).is_file():
        raise HTTPException(404, "Source video not found")
    return asset


def _save_sources(job_id, sources):
    job_dir = JOBS / job_id / "inputs"
    job_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, (name, source) in enumerate(sources, start=1):
        path = job_dir / f"source_{index:02d}.mp4"
        shutil.copyfile(source, path)
        metadata = probe(path)
        assets.append({"id": f"source_{index:02d}", "name": Path(name).name, "path": str(path), **metadata})
    return assets


def _queue(job_id, instruction, options, assets):
    if not assets or len(assets) > MAX_FILES:
        raise HTTPException(400, f"Upload 1–{MAX_FILES} videos")
    if sum(asset["duration"] for asset in assets) > MAX_TOTAL_SECONDS:
        raise HTTPException(400, "Combined video duration exceeds 15 minutes")
    create_job(job_id, instruction, options, assets)
    _submit(job_id)
    return {"id": job_id, "status": "queued"}


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/jobs")
def jobs():
    return list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    return _get(job_id)


@app.get("/api/jobs/{job_id}/assets/{asset_id}/video")
def source_video(job_id: str, asset_id: str):
    asset = _asset(job_id, asset_id)
    return FileResponse(asset["path"], media_type="video/mp4")


@app.get("/api/jobs/{job_id}/assets/{asset_id}/frame")
def source_frame(job_id: str, asset_id: str, at: float = Query(default=0, ge=0, allow_inf_nan=False)):
    asset = _asset(job_id, asset_id)
    moment = min(round(at * 2) / 2, max(0, asset["duration"] - 0.1))
    frame = JOBS / job_id / "previews" / f"{asset_id}_{round(moment * 2):05d}.jpg"
    try:
        preview_frame(asset["path"], moment, frame)
    except RuntimeError as exc:
        raise HTTPException(500, f"Could not create preview frame: {exc}") from exc
    return FileResponse(frame, media_type="image/jpeg")


@app.post("/api/jobs")
async def create(
    files: list[UploadFile] = File(...),
    instruction: str = Form(...),
    target_seconds: int = Form(35),
    aspect: str = Form("9:16"),
    topics: str = Form(""),
):
    if not 1 <= len(files) <= MAX_FILES:
        raise HTTPException(400, f"Upload 1–{MAX_FILES} videos")
    if not instruction.strip():
        raise HTTPException(400, "Enter an editing instruction")
    if aspect not in {"16:9", "9:16"} or not 1 <= target_seconds <= 600:
        raise HTTPException(400, "Invalid output settings")
    job_id = uuid.uuid4().hex
    directory = JOBS / job_id / "inputs"
    directory.mkdir(parents=True, exist_ok=True)
    assets = []
    total_bytes = 0
    try:
        for index, upload in enumerate(files, start=1):
            if Path(upload.filename or "").suffix.lower() != ".mp4":
                raise HTTPException(400, "Only MP4 inputs are supported")
            path = directory / f"source_{index:02d}.mp4"
            with path.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "Upload exceeds 2 GB")
                    destination.write(chunk)
            try:
                metadata = probe(path)
            except Exception as exc:
                raise HTTPException(400, f"Cannot read {upload.filename}: {exc}") from exc
            assets.append({"id": f"source_{index:02d}", "name": Path(upload.filename).name, "path": str(path), **metadata})
        options = {"target_seconds": target_seconds, "aspect": aspect, "topics": topics, "subtitles": True}
        return _queue(job_id, instruction.strip(), options, assets)
    except Exception:
        shutil.rmtree(JOBS / job_id, ignore_errors=True)
        raise


@app.post("/api/demo")
def demo():
    samples = sorted(DEMO.glob("*.mp4"))
    if len(samples) < 2:
        raise HTTPException(409, "Demo media is missing. Run scripts/make_demo.py first.")
    job_id = uuid.uuid4().hex
    assets = _save_sources(job_id, [(sample.name, sample) for sample in samples[:3]])
    return _queue(
        job_id,
        "Create a 25-40 second recap covering the problem, solution, and demonstration result; remove long pauses, add English subtitles, and export vertically.",
        {"aspect": "9:16", "topics": [], "subtitles": True},
        assets,
    )


@app.post("/api/jobs/{job_id}/revise")
@_serialized_revision
def revise(job_id: str, body: Revision):
    current = _get(job_id)
    if current["status"] not in {"complete", "needs_review"}:
        raise HTTPException(409, "This job is not ready for revision")
    options = dict(current["options"])
    if body.target_seconds is not None:
        options["target_seconds"] = body.target_seconds
        options.pop("min_seconds", None)
        options.pop("max_seconds", None)
    if body.aspect is not None:
        if body.aspect not in {"16:9", "9:16"}:
            raise HTTPException(400, "Invalid aspect ratio")
        options["aspect"] = body.aspect
    if body.topics is not None:
        options["topics"] = body.topics
    elif re.search(r"\b(?:cover(?:ing)?|include|including|about)\b", body.instruction, re.I):
        options["topics"] = []
    update_job(job_id, instruction=body.instruction, options=options, status="queued", report={}, error=None)
    _submit(job_id, revision=True)
    return {"id": job_id, "status": "queued"}


@app.post("/api/jobs/{job_id}/timeline")
@_serialized_revision
def edit_timeline(job_id: str, body: TimelineEdit):
    current = _get(job_id)
    if current["status"] not in {"complete", "needs_review"}:
        raise HTTPException(409, "This job is not ready for timeline changes")
    clips = []
    for input_clip in body.clips:
        clips.append({
            "asset_id": input_clip.asset_id,
            "start": round(input_clip.start, 3),
            "end": round(input_clip.end, 3),
            "evidence_ids": [],
            "reason": "Manual timeline edit",
            "required": False,
            "score": 0.0,
        })
    try:
        validate_timeline(clips, current["assets"])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    update_job(job_id, status="queued", report={}, error=None)
    _submit(job_id, revision=True, manual_timeline=clips)
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}/{artifact}")
def artifact(job_id: str, artifact: str):
    record = _get(job_id)
    if artifact == "timeline.json":
        return JSONResponse(
            {
                "job_id": job_id,
                "version": record["version"],
                "sources": [
                    {key: asset[key] for key in ("id", "name", "duration", "width", "height")}
                    for asset in record["assets"]
                ],
                "clips": record["timeline"],
            },
            headers={"Content-Disposition": 'attachment; filename="timeline.json"'},
        )
    if artifact == "report.json":
        return JSONResponse(
            record["report"],
            headers={"Content-Disposition": 'attachment; filename="report.json"'},
        )
    names = {"video": "final.mp4", "subtitles": "captions.srt"}
    if artifact not in names:
        raise HTTPException(404, "Artifact not found")
    if record["status"] not in {"complete", "needs_review"} or not record["report"].get("outputs"):
        raise HTTPException(409, "Current export is not ready")
    path = JOBS / job_id / "output" / names[artifact]
    if not path.is_file():
        raise HTTPException(404, "Artifact is not ready")
    return FileResponse(path, filename=names[artifact] if artifact == "subtitles" else None)
