#!/usr/bin/env python3
"""
Turn a raw recording of record_demo.py into the published mp4: trim the page-load start,
mix the voice-over clips at the times logged in narration.json and encode H.264/AAC.

  python scripts/demo_video/mux_demo.py demo_raw docs/demo_video/wmnc2026_live_demo.mp4
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

NARR = Path(__file__).resolve().parent / "static" / "narr"


def main(raw: str, out: str):
    meta = json.loads((Path(raw) / "narration.json").read_text())
    video = Path(raw) / meta["video"]
    trim = meta["trim"]
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-ss", f"{trim:.3f}", "-i", str(video)]
    parts = []
    for i, e in enumerate(meta["events"], start=1):
        cmd += ["-i", str(NARR / e["clip"])]
        ms = max(0, int((e["at"] - trim) * 1000))
        parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    n = len(meta["events"])
    mix = "".join(f"[a{i}]" for i in range(1, n + 1))
    graph = ";".join(parts) + f";{mix}amix=inputs={n}:normalize=0:duration=longest,apad[aout]"
    cmd += ["-filter_complex", graph, "-map", "0:v", "-map", "[aout]", "-shortest",
            "-r", "25", "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
