"""Offline service/API integration; INJECTED cases are never called real E2E."""
import asyncio
import importlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import av
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from clipagent import media, service, storage

TRACES = []


async def request(application, method, path, body=b"", content_type=None):
    """Exercise the actual ASGI router without an optional HTTP client dependency."""
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    route, _, query = path.partition("?")
    await application({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": route, "raw_path": route.encode(), "query_string": query.encode(),
        "headers": [(b"content-type", content_type.encode())] if content_type else [],
        "client": ("127.0.0.1", 1), "server": ("localhost", 80), "root_path": "",
    }, receive, send)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, payload


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_temp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.media_temp.name) / "silent.mp4"
        subprocess.run([media.FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "testsrc2=s=160x90:r=15", "-t", "3",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.source)],
                       check=True, capture_output=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.media_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.futures = []
        for obj, name, value in [(storage, "DATABASE", self.root / "jobs.sqlite"),
                                 (storage, "JOBS", self.root / "jobs"),
                                 (service, "JOBS", self.root / "jobs")]:
            p = patch.object(obj, name, value)
            p.start()
            self.addCleanup(p.stop)
        storage.init_db()
        self.api = importlib.import_module("app")
        p = patch.object(self.api, "JOBS", self.root / "jobs")
        p.start()
        self.addCleanup(p.stop)
        original_submit = service.submit

        def track(*args, **kwargs):
            future = original_submit(*args, **kwargs)
            self.futures.append(future)
            return future

        p = patch.object(self.api, "submit", side_effect=track)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.wait)
        self.kind = "real local media integration (no speech model)"
        self.injection = None
        self.job_id = None
        self.addCleanup(self.trace)

    def wait(self):
        for future in self.futures:
            future.result(timeout=180)

    def trace(self):
        self.wait()
        job = storage.get_job(self.job_id) if self.job_id else None
        if job:
            # Keep traces portable and avoid retaining temporary machine paths.
            for asset in job["assets"]:
                asset["path"] = Path(asset["path"]).name
        TRACES.append({"test": self.id(), "classification": self.kind,
                       "injected_error_or_fixture": self.injection, "job": job})

    def call(self, method, path, value=None):
        body = json.dumps(value).encode() if value is not None else b""
        status, payload = asyncio.run(request(self.api.app, method, path, body,
                                              "application/json" if value is not None else None))
        return status, payload

    def upload(self, source=None, topics="", target_seconds=3):
        source = source or self.source
        boundary = "clipagent-test-boundary"
        parts = []
        for key, value in {"instruction": "Make a short recap", "target_seconds": str(target_seconds),
                           "aspect": "16:9", "topics": topics}.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="sample.mp4"\r\nContent-Type: video/mp4\r\n\r\n'.encode() + source.read_bytes() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        status, body = asyncio.run(request(self.api.app, "POST", "/api/jobs", b"".join(parts),
                                          f"multipart/form-data; boundary={boundary}"))
        if status == 200:
            self.job_id = json.loads(body)["id"]
        return status, body

    def completed_upload(self, **kwargs):
        status, body = self.upload(**kwargs)
        self.assertEqual(status, 200, body)
        self.wait()
        job = storage.get_job(self.job_id)
        self.assertIn(job["status"], {"complete", "needs_review"}, job)
        return job

    def test_real_silent_upload_render_decode_manual_edit_revision(self):
        job = self.completed_upload(topics="quantum zebras")
        self.assertEqual(job["status"], "needs_review")
        self.assertFalse(job["report"]["topic_evidence"][0]["verified"])
        self.assertEqual(job["transcript"], [])
        self.assertTrue(job["report"]["checks"]["decodable"])
        status, video = self.call("GET", f"/api/jobs/{self.job_id}/video")
        self.assertEqual(status, 200)
        self.assertGreater(len(video), 1000)
        status, frame = self.call("GET", f"/api/jobs/{self.job_id}/assets/source_01/frame?at=0.5")
        self.assertEqual(status, 200)
        self.assertTrue(frame.startswith(b"\xff\xd8"))
        status, body = self.call("POST", f"/api/jobs/{self.job_id}/timeline",
                                {"clips": [{"asset_id": "source_01", "start": 0.5, "end": 2.0}]})
        self.assertEqual(status, 200, body)
        self.wait()
        edited = storage.get_job(self.job_id)
        self.assertEqual(edited["version"], job["version"] + 1)
        self.assertAlmostEqual(edited["report"]["checks"]["duration"], 1.5, delta=0.2)
        self.assertFalse(edited["report"]["topic_evidence"][0]["verified"])
        status, body = self.call("POST", f"/api/jobs/{self.job_id}/revise",
                                {"instruction": "Make it vertical", "aspect": "9:16"})
        self.assertEqual(status, 200, body)
        self.wait()
        revised = storage.get_job(self.job_id)
        self.assertEqual(revised["version"], edited["version"] + 1)
        self.assertEqual(revised["report"]["checks"]["width"], 720)
        self.assertEqual(revised["report"]["checks"]["height"], 1280)
        self.assertEqual(sum(e["phase"] == "replanning" for e in revised["events"]), 2)

    def test_real_generated_speech_cached_model(self):
        self.kind = "real local speech media E2E (local speech synthesis and cached ASR)"
        snapshots = list((media.MODELS / "models--Systran--faster-whisper-tiny.en" / "snapshots").glob("*/model.bin"))
        if not shutil.which("say") or not snapshots:
            self.skipTest("Requires local say and a pre-existing tiny.en cache; no download allowed")
        audio = self.root / "speech.aiff"
        subprocess.run(["say", "-o", str(audio), "The problem is slow search. The solution is a short video."],
                       check=True, capture_output=True, timeout=30)
        with av.open(str(audio)) as container:
            if not container.duration or not any(container.decode(audio=0)):
                self.skipTest("Installed macOS say produced an empty AIFF in this environment; speech synthesis E2E not exercised")
        source = self.root / "speech.mp4"
        subprocess.run([media.FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=15", "-i", str(audio),
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)],
                       check=True, capture_output=True, timeout=30)
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                                     "CLIPAGENT_WHISPER_MODEL": str(snapshots[0].parent)}):
            job = self.completed_upload(source=source, topics="problem")
        self.assertTrue(job["transcript"], job)
        self.assertEqual(job["status"], "complete", job["report"])
        self.assertTrue(job["report"]["topic_evidence"][0]["verified"])
        self.assertGreater(job["report"]["checks"]["subtitle_cues"], 0)
        self.assertTrue(job["report"]["checks"]["subtitle_within_video"])

    def test_real_public_audio_cached_model(self):
        self.kind = "real local public audio E2E (generated video, existing WAV, cached ASR)"
        wav = Path(__file__).resolve().parents[1] / "sample_data" / "6930-75918-0003.wav"
        snapshots = list((media.MODELS / "models--Systran--faster-whisper-tiny.en" / "snapshots").glob("*/model.bin"))
        if not wav.is_file() or not snapshots:
            self.skipTest("Requires existing public WAV and tiny.en cache; no download allowed")
        source = self.root / "public-speech.mp4"
        subprocess.run([media.FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "testsrc2=s=160x90:r=15", "-i", str(wav),
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)],
                       check=True, capture_output=True, timeout=30)
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                                     "CLIPAGENT_WHISPER_MODEL": str(snapshots[0].parent)}):
            job = self.completed_upload(source=source, target_seconds=round(media.probe(source)["duration"]))
        self.assertTrue(job["transcript"], job)
        self.assertEqual(job["status"], "complete", job["report"])
        self.assertGreater(job["report"]["checks"]["subtitle_cues"], 0)
        self.assertTrue(job["report"]["checks"]["subtitle_within_video"])
        self.assertTrue(job["report"]["checks"]["decodable"])

    def injected(self, description):
        self.kind = "INJECTED failure/control-flow integration; not real E2E"
        self.injection = description

    def test_injected_render_failure_hides_previous_export(self):
        self.completed_upload()
        previous = (self.root / "jobs" / self.job_id / "output" / "final.mp4").read_bytes()
        self.injected("render raises RuntimeError after writing a partial staging file")

        def broken(assets, timeline, srt, aspect, directory):
            (Path(directory) / "final.mp4").write_bytes(b"INJECTED partial output")
            raise RuntimeError("INJECTED renderer crash")

        with patch.object(service, "render", side_effect=broken):
            status, _ = self.call("POST", f"/api/jobs/{self.job_id}/revise", {"instruction": "Try again"})
            self.assertEqual(status, 200)
            self.wait()
        job = storage.get_job(self.job_id)
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["report"], {})
        self.assertIn("INJECTED", job["error"])
        self.assertEqual(self.call("GET", f"/api/jobs/{self.job_id}/video")[0], 409)
        self.assertEqual(self.call("GET", f"/api/jobs/{self.job_id}/subtitles")[0], 409)
        self.assertEqual((self.root / "jobs" / self.job_id / "output" / "final.mp4").read_bytes(), previous)
        self.assertEqual(list((self.root / "jobs" / self.job_id).glob("render-*")), [])

    def test_injected_decode_rejection_is_safe_failure(self):
        self.injected("verify returns decodable=False; actual local render still runs")
        with patch.object(service, "verify", return_value={"decodable": False}):
            self.assertEqual(self.upload()[0], 200)
            self.wait()
        self.assertEqual(storage.get_job(self.job_id)["status"], "failed")
        self.assertEqual(self.call("GET", f"/api/jobs/{self.job_id}/video")[0], 409)

    def test_injected_duration_mismatch_bounded_to_three_renders(self):
        self.injected("verified duration forced to 99s and repair returns unchanged timeline; real render/decode each attempt")
        real_verify = service.verify

        def mismatch(*args):
            result = real_verify(*args)
            result["duration"] = 99
            return result

        with patch.object(service, "verify", side_effect=mismatch), patch.object(
            service, "repair_duration", side_effect=lambda timeline, *args: (timeline, "INJECTED non-converging repair")
        ):
            job = self.completed_upload()
        self.assertEqual(job["report"]["render_attempts"], 3)
        self.assertEqual(len(job["report"]["repairs"]), 2)
        self.assertFalse(job["report"]["checks"]["duration_ok"])
        self.assertEqual(job["status"], "needs_review")

    def test_injected_duration_mismatch_recovers(self):
        self.injected("first verified duration forced to 99s; seeded two-clip planner fixture; actual repair/render/decode")
        clips = [{"asset_id": "source_01", "start": 0, "end": 1, "evidence_ids": [], "required": True},
                 {"asset_id": "source_01", "start": 1.5, "end": 2.5, "evidence_ids": [], "required": False}]
        real_verify = service.verify
        calls = []

        def mismatch_once(*args):
            result = real_verify(*args)
            if not calls:
                result["duration"] = 99
            calls.append(result)
            return result

        with patch.object(service, "build_timeline", return_value=(clips, [])), patch.object(service, "verify", side_effect=mismatch_once):
            job = self.completed_upload()
        self.assertEqual(job["report"]["render_attempts"], 2)
        self.assertEqual(len(job["report"]["repairs"]), 1)
        self.assertEqual(len(job["timeline"]), 1)
        self.assertTrue(job["timeline"][0]["required"])
        self.assertTrue(job["report"]["checks"]["duration_ok"])

    def test_injected_queue_failure_and_concurrent_revision(self):
        self.completed_upload()
        self.injected("submission held to test competing requests, then executor rejection")
        with patch.object(self.api, "submit", return_value=None):
            with ThreadPoolExecutor(max_workers=2) as workers:
                futures = [workers.submit(self.call, "POST", f"/api/jobs/{self.job_id}/revise",
                                          {"instruction": "Try again"}) for _ in range(2)]
                statuses = sorted(f.result()[0] for f in futures)
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(self.call("GET", f"/api/jobs/{self.job_id}/video")[0], 409)
        storage.update_job(self.job_id, status="needs_review")
        with patch.object(self.api, "submit", side_effect=RuntimeError("INJECTED executor shutdown")):
            status, _ = self.call("POST", f"/api/jobs/{self.job_id}/revise", {"instruction": "Try again"})
        self.assertEqual(status, 503)
        self.assertEqual(storage.get_job(self.job_id)["status"], "failed")

    def test_real_invalid_media_cleanup_and_invalid_edit(self):
        corrupt = self.root / "corrupt.mp4"
        corrupt.write_bytes(b"This is not a video")
        self.assertEqual(self.upload(source=corrupt)[0], 400)
        self.assertEqual(list((self.root / "jobs").iterdir()), [])
        job = self.completed_upload()
        status, _ = self.call("POST", f"/api/jobs/{self.job_id}/timeline",
                              {"clips": [{"asset_id": "source_01", "start": 0, "end": 300}]})
        self.assertEqual(status, 400)
        self.assertEqual(storage.get_job(self.job_id)["version"], job["version"])
        self.assertEqual(self.call("GET", f"/api/jobs/{self.job_id}/assets/source_01/frame?at=inf")[0], 422)
        self.assertEqual(self.call("GET", "/api/jobs/does-not-exist")[0], 404)


if __name__ == "__main__":
    unittest.main()
