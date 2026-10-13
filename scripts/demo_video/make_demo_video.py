#!/usr/bin/env python3
"""
Record a live demo session against the running platform and render it as an MP4.

  python scripts/demo_video/make_demo_video.py            # record + render
  python scripts/demo_video/make_demo_video.py --render   # re-render docs/demo_video/session.json

Recording runs every scene command for real (scripts/demo_cli.py) and stores the
command, its exact output, wall-clock duration and timestamp in session.json.
Rendering turns that session into a terminal-style video; it never alters outputs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "demo_video"
SESSION = OUT_DIR / "session.json"
VIDEO = OUT_DIR / "wmnc2026_demo.mp4"

SCENES = [
    {"title": "The whole stack is live",
     "tag": "Reviewers 1 & 4: live CAPIF, real execution",
     "caption": "OpenCAPIF, four CAMARA/NEF providers, an Open5GS 5G core and UERANSIM UEs are running. "
                "The backend discovered the published CAMARA APIs over CAPIF (mTLS).",
     "cmds": ["status"]},
    {"title": "Dry-run vs. live execution",
     "tag": "Reviewer 1: the old Fig. 2 showed dry_run: true",
     "caption": "dry_run: true validates the plan, including the live CAPIF registry check (L3), but does not call "
                "the provider. dry_run: false executes CAMARA QoD -> NEF -> Open5GS PCF and returns AVAILABLE.",
     "cmds": ["run s1", "run s1 --live", "core-evidence"]},
    {"title": "Location and an ambiguous intent",
     "tag": "Reviewer 1: Scenario 3 and wrong-but-registered services",
     "caption": "S3 is dataset entry edge_003 (ground truth: QoD). L3 only checks that the chosen service is "
                "published, so a wrong-but-registered choice still executes: the validator guarantees "
                "well-formed calls, not intent correctness.",
     "cmds": ["run s2 --live", "run s3 --live"]},
    {"title": "Switching LLM backends at runtime",
     "tag": "Reviewer 2: provider-agnostic planning",
     "caption": "POST /config/provider switches GPT-4o-mini, Claude Haiku 4.5 and Gemini 2.5 Flash without a restart; "
                "all three produce the same CAMARA payload. Planning time differs per provider.",
     "cmds": ["compare s1"]},
    {"title": "Which layer catches what?",
     "tag": "Reviewers 1 & 3: per-layer difficulties, feedback, latency",
     "caption": "Faults are injected into correct plans. Each is caught by its target layer; the LLM feedback loop "
                "repairs L1/L2 payload faults in one iteration but cannot repair a service-level (L3) fault.",
     "cmds": ["faults --per-fault 2"]},
    {"title": "Scalability and the external LLM API",
     "tag": "Reviewer 2: latency breakdown, scalability, LLM dependency",
     "caption": "Without the LLM the platform serves well over 100 req/s with live L3 checks; with GPT-4o-mini the "
                "latency stays at about 2.6 s while throughput scales with concurrency: the LLM API is the bottleneck.",
     "cmds": ["load"]},
    {"title": "Evaluation, ablations and repository consistency",
     "tag": "Reviewers 2 & 4: benchmarking and the 60-entry pilot",
     "caption": "300 unique intents. The keyword rules were written for the 60-entry pilot (archived), hence 60/60 "
                "there and 190/240 on held-out intents. Without schema grounding GPT-4o-mini drops to 16.3%.",
     "cmds": ["results"]},
]

TITLE = "From Natural Language to Live 5G API Calls"
SUBTITLE = "A CAPIF-compliant, multi-LLM intent orchestration platform  |  WMNC 2026 demo"
REPO = "github.com/doadurak/mini-telco-platform"


# ── recording ────────────────────────────────────────────────────────────────

def record() -> dict:
    session = {"recorded_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
               "host": "single 16 GB host (WSL2 + Docker Desktop)", "scenes": []}
    for sc in SCENES:
        runs = []
        for c in sc["cmds"]:
            shown = f"python scripts/demo_cli.py {c}"
            print(f"$ {shown}", flush=True)
            t0 = time.perf_counter()
            p = subprocess.run(f"{sys.executable} scripts/demo_cli.py {c}", shell=True, cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            secs = time.perf_counter() - t0
            out = (p.stdout + (p.stderr if p.returncode else "")).rstrip("\n")
            print(out + f"\n[{secs:.1f} s, exit {p.returncode}]\n", flush=True)
            runs.append({"cmd": shown, "output": out, "seconds": round(secs, 1), "exit": p.returncode})
        session["scenes"].append({**{k: sc[k] for k in ("title", "tag", "caption")}, "runs": runs})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return session


# ── rendering ────────────────────────────────────────────────────────────────

W, H, FPS = 1920, 1080, 15
BG, FG, DIM, ACC, OKC, BAR = (24, 26, 31), (220, 223, 228), (140, 146, 156), (97, 175, 239), (152, 195, 121), (34, 37, 44)
PROMPT = "turkad@testbed:~/mini-telco-platform$ "


def _fonts():
    from PIL import ImageFont
    import matplotlib
    d = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    f = lambda n, s: ImageFont.truetype(str(d / n), s)  # noqa: E731
    return {"mono": f("DejaVuSansMono.ttf", 23), "mono_b": f("DejaVuSansMono-Bold.ttf", 23),
            "sans": f("DejaVuSans.ttf", 27), "sans_b": f("DejaVuSans-Bold.ttf", 34),
            "tag": f("DejaVuSans.ttf", 25), "big": f("DejaVuSans-Bold.ttf", 60), "mid": f("DejaVuSans.ttf", 34)}


class Renderer:
    def __init__(self, path: Path):
        import imageio_ffmpeg
        from PIL import Image, ImageDraw
        self.Image, self.ImageDraw, self.f = Image, ImageDraw, _fonts()
        self.writer = imageio_ffmpeg.write_frames(str(path), (W, H), fps=FPS, codec="libx264",
                                                  pix_fmt_out="yuv420p", macro_block_size=8,
                                                  output_params=["-crf", "20"])
        self.writer.send(None)
        self.frames = 0

    def emit(self, img, seconds: float):
        data = img.tobytes()
        for _ in range(max(1, round(seconds * FPS))):
            self.writer.send(data)
            self.frames += 1

    def close(self):
        self.writer.close()

    def card(self, lines, footer=""):
        img = self.Image.new("RGB", (W, H), BG)
        d = self.ImageDraw.Draw(img)
        y = H // 2 - 40 * len(lines)
        for text, font, color in lines:
            w = d.textlength(text, font=self.f[font])
            d.text(((W - w) / 2, y), text, font=self.f[font], fill=color)
            y += 95 if font == "big" else 60
        if footer:
            w = d.textlength(footer, font=self.f["tag"])
            d.text(((W - w) / 2, H - 90), footer, font=self.f["tag"], fill=DIM)
        return img

    def frame(self, idx, scene, term_lines):
        img = self.Image.new("RGB", (W, H), BG)
        d = self.ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 86], fill=BAR)
        d.text((40, 24), f"Scene {idx}  |  {scene['title']}", font=self.f["sans_b"], fill=FG)
        tw = d.textlength(scene["tag"], font=self.f["tag"])
        d.text((W - tw - 40, 30), scene["tag"], font=self.f["tag"], fill=ACC)
        y = 112
        for text, kind in term_lines[-27:]:
            if kind == "prompt":
                d.text((50, y), PROMPT, font=self.f["mono"], fill=OKC)
                d.text((50 + d.textlength(PROMPT, font=self.f["mono"]), y), text, font=self.f["mono_b"], fill=FG)
            else:
                d.text((50, y), text, font=self.f["mono"], fill=DIM if kind == "meta" else FG)
            y += 30
        d.rectangle([0, H - 150, W, H], fill=BAR)
        for i, ln in enumerate(textwrap.wrap(scene["caption"], 118)[:3]):
            d.text((40, H - 138 + i * 40), ln, font=self.f["sans"], fill=FG)
        return img


def render(session: dict) -> Path:
    r = Renderer(VIDEO)
    date = session["recorded_at"][:10]
    r.emit(r.card([(TITLE, "big", FG), (SUBTITLE, "mid", DIM),
                   (f"Live session recorded {date}: real system, real calls, unedited outputs", "mid", ACC)],
                  footer=REPO), 5)
    r.emit(r.card([("Each scene answers a CNSM 2026 review comment.", "mid", FG),
                   ("Outputs are shown as recorded (docs/demo_video/session.json); MSISDNs are masked.", "mid", DIM)]), 4)
    for i, sc in enumerate(session["scenes"], 1):
        r.emit(r.card([(f"Scene {i}: {sc['title']}", "big", FG), (sc["tag"], "mid", ACC)]), 3)
        for run in sc["runs"]:
            term = []
            for k in range(0, len(run["cmd"]) + 1, 2):  # typing
                r.emit(r.frame(i, sc, term + [(run["cmd"][:k] + "█", "prompt")]), 1 / FPS)
            term.append((run["cmd"], "prompt"))
            r.emit(r.frame(i, sc, term + [(f"running ... (real duration {run['seconds']:.1f} s)", "meta")]),
                   min(2.5, max(0.8, run["seconds"] / 4)))
            lines = run["output"].splitlines()
            for j in range(0, len(lines), 3):  # output appears line by line
                r.emit(r.frame(i, sc, term + [(l, "out") for l in lines[:j + 3]]), 0.12)
            term += [(l, "out") for l in lines] + [(f"[completed in {run['seconds']:.1f} s]", "meta")]
            r.emit(r.frame(i, sc, term), min(15, max(7, 0.5 * len(lines))))
    r.emit(r.card([("Code, testbed, datasets, recorded runs", "mid", FG), (REPO, "big", ACC),
                   ("start.sh  |  scripts/demo_cli.py  |  scripts/demo_video/", "mid", DIM)]), 5)
    r.close()
    print(f"wrote {VIDEO} ({r.frames / FPS:.0f} s)")
    return VIDEO


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="only re-render the stored session")
    a = ap.parse_args()
    session = json.loads(SESSION.read_text(encoding="utf-8")) if a.render else record()
    render(session)


if __name__ == "__main__":
    main()
