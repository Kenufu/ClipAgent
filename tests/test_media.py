import subprocess
import tempfile
import unittest
from pathlib import Path

from clipagent.media import FFMPEG, preview_frame, probe, render, verify


class MediaTests(unittest.TestCase):
    def test_render_and_full_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for index, color in enumerate(("red", "blue"), start=1):
                path = root / f"source_{index}.mp4"
                subprocess.run([
                    FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=24",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                    "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(path),
                ], check=True)
                sources.append({"id": f"source_{index}", "path": str(path), **probe(path)})
            timeline = [
                {"asset_id": "source_2", "start": 0.25, "end": 1.5},
                {"asset_id": "source_1", "start": 0.5, "end": 1.75},
            ]
            final, srt = render(sources, timeline, "", "9:16", root / "output")
            checks = verify(final, "9:16")
            self.assertTrue(checks["decodable"])
            self.assertTrue(checks["has_audio"])
            self.assertEqual((checks["width"], checks["height"]), (720, 1280))
            self.assertAlmostEqual(checks["duration"], 2.5, delta=0.25)
            self.assertTrue(srt.exists())

            frame = preview_frame(sources[0]["path"], 0.5, root / "previews" / "frame.jpg")
            self.assertTrue(frame.is_file())
            self.assertGreater(frame.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
