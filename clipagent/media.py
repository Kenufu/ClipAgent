import os
import re
import shutil
import subprocess
from pathlib import Path

import av
import imageio_ffmpeg

from .config import MODELS

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
_model = None


def probe(path):
    with av.open(str(path)) as container:
        videos = [stream for stream in container.streams if stream.type == "video"]
        audios = [stream for stream in container.streams if stream.type == "audio"]
        if not videos:
            raise ValueError("File has no video stream")
        stream = videos[0]
        duration = (container.duration or 0) / 1_000_000
        if not duration and stream.duration:
            duration = float(stream.duration * stream.time_base)
        if duration <= 0:
            raise ValueError("Could not determine video duration")
        return {
            "duration": round(duration, 3),
            "width": stream.width,
            "height": stream.height,
            "fps": round(float(stream.average_rate or 0), 3),
            "has_audio": bool(audios),
            "video_codec": stream.codec_context.name,
            "size_bytes": Path(path).stat().st_size,
        }


def _whisper():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        MODELS.mkdir(parents=True, exist_ok=True)
        _model = WhisperModel(
            os.environ.get("CLIPAGENT_WHISPER_MODEL", "tiny.en"),
            device="cpu",
            compute_type="int8",
            download_root=str(MODELS),
            local_files_only=True,
        )
    return _model


def transcribe(path, asset_id):
    segments, _ = _whisper().transcribe(
        str(path), language="en", beam_size=5, word_timestamps=True,
        condition_on_previous_text=False,
    )
    cues = []
    words = []

    def flush():
        if not words:
            return
        cues.append({
            "id": f"{asset_id}:t{len(cues) + 1}",
            "asset_id": asset_id,
            "start": round(words[0][0], 3),
            "end": round(words[-1][1], 3),
            "text": "".join(word[2] for word in words).strip(),
            "words": [
                {"start": round(start, 3), "end": round(end, 3), "text": text}
                for start, end, text in words
            ],
        })
        words.clear()

    for segment in segments:
        if not segment.words:
            cues.append({
                "id": f"{asset_id}:t{len(cues) + 1}", "asset_id": asset_id,
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3), "text": segment.text.strip(),
                "words": [],
            })
            continue
        for word in segment.words:
            words.append((float(word.start), float(word.end), word.word))
            if re.search(r"[.!?]$", word.word.strip()) or word.end - words[0][0] >= 12:
                flush()
    flush()
    return [cue for cue in cues if cue["text"] and cue["end"] > cue["start"]]


def _run(args, timeout=240, cwd=None):
    try:
        completed = subprocess.run(
            [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args],
            capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"FFmpeg timed out after {timeout} seconds") from exc
    if completed.returncode:
        raise RuntimeError((completed.stderr or "FFmpeg failed")[-3000:])
    return completed


def render(assets, timeline, subtitles, aspect, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(exist_ok=True)
    target_width, target_height = (720, 1280) if aspect == "9:16" else (1280, 720)
    vf = (
        f"fps=30,scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )
    paths = []
    by_id = {asset["id"]: asset for asset in assets}
    for index, clip in enumerate(timeline):
        asset = by_id[clip["asset_id"]]
        destination = parts_dir / f"part_{index:03d}.mp4"
        duration = clip["end"] - clip["start"]
        args = ["-ss", str(clip["start"]), "-i", asset["path"]]
        if not asset["has_audio"]:
            args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        args += ["-t", str(duration), "-map", "0:v:0", "-map", "0:a:0" if asset["has_audio"] else "1:a:0"]
        args += ["-vf", vf, "-af", "aresample=async=1:first_pts=0,apad", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(destination)]
        _run(args)
        paths.append(destination)

    concat_list = output_dir / "concat.txt"
    concat_list.write_text("".join(f"file '{path}'\n" for path in paths), encoding="utf-8")
    draft = output_dir / "draft.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(draft)])
    srt = output_dir / "captions.srt"
    srt.write_text(subtitles, encoding="utf-8")
    final = output_dir / "final.mp4"
    if subtitles.strip():
        _run(["-i", "draft.mp4", "-vf", "subtitles=captions.srt:force_style='FontSize=12,MarginV=40,Outline=1'", "-c:v", "libx264",
              "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "copy",
              "-movflags", "+faststart", "final.mp4"], cwd=output_dir)
    else:
        shutil.copyfile(draft, final)
    return final, srt


def verify(path, expected_aspect):
    metadata = probe(path)
    _run(["-i", str(path), "-f", "null", "-"], timeout=300)
    ratio = metadata["width"] / metadata["height"]
    expected = 9 / 16 if expected_aspect == "9:16" else 16 / 9
    return {
        "decodable": True,
        "has_audio": metadata["has_audio"],
        "duration": metadata["duration"],
        "width": metadata["width"],
        "height": metadata["height"],
        "aspect_ok": abs(ratio - expected) < 0.02,
    }
