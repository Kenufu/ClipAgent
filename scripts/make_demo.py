"""Create three short, locally narrated MP4 files for the one-click demo."""

import subprocess
from pathlib import Path

import av
import imageio_ffmpeg

from clipagent.config import DEMO

SAMPLES = [
    (
        "01_problem", "PROBLEM", "#234C63",
        "The problem is that long lecture recordings make important ideas hard to find. "
        "A viewer has to search through pauses and repeated explanations. "
        "This wastes time when they only need a short recap.",
    ),
    (
        "02_solution", "SOLUTION", "#1D7867",
        "Our solution is to transcribe the source and locate evidence for each requested topic. "
        "The agent builds a source linked timeline and removes long pauses between spoken ideas. "
        "It then renders the selected clips into a compact video.",
    ),
    (
        "03_result", "DEMONSTRATION RESULT", "#A66842",
        "The demonstration result is a playable short video with readable subtitles. "
        "Every selected clip points back to its original source and time. "
        "A final check confirms the duration, audio, and frame size.",
    ),
]


def main():
    DEMO.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for filename, title, color, speech in SAMPLES:
        audio = DEMO / f"{filename}.aiff"
        output = DEMO / f"{filename}.mp4"
        subprocess.run(["say", "-v", "Samantha", "-o", str(audio), speech], check=True)
        with av.open(str(audio)) as container:
            if not container.duration:
                raise RuntimeError("System speech did not generate audio")
            duration = container.duration / 1_000_000 + 2.0
        filter_text = (
            "drawtext=text='" + title + "':fontcolor=white:fontsize=62:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        )
        subprocess.run([
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=30",
            "-i", str(audio), "-t", f"{duration:.3f}", "-vf", filter_text,
            "-af", "adelay=800,apad", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(output),
        ], check=True)
        print(f"Created {output.name} ({duration:.1f}s)")


if __name__ == "__main__":
    main()
