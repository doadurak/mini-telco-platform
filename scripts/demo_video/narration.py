#!/usr/bin/env python3
"""
English voice-over for the demo video. Each scene is a list of sentences; every sentence is
one audio clip and one subtitle line.

  pip install edge-tts mutagen
  python scripts/demo_video/narration.py          # writes static/narr/*.mp3 + durations.json
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

VOICE = "en-US-AriaNeural"
RATE = "-4%"
OUT = Path(__file__).resolve().parent / "static" / "narr"

NARRATION = {
    "intro": [
        "Live demo: from a natural-language request to a validated 5G network API call.",
    ],
    "arch": [
        "A two-phase LLM planner selects a CAMARA service, then builds its payload.",
        "Three validation layers check the schema, the telecom rules and the live OpenCAPIF registry, "
        "before anything reaches the Open5GS core.",
    ],
    "status": [
        "Step one: the testbed. OpenCAPIF, the CAMARA and NEF providers, Open5GS, "
        "and three simulated phones are all running.",
    ],
    "dry": [
        "Step two: a dry run. We ask for video-streaming quality for thirty minutes.",
        "The plan passes all three layers, but nothing is sent to the network yet.",
    ],
    "live": [
        "Step three: the same request, live.",
    ],
    "live_res": [
        "The NEF forwards it to the Open5GS policy function, which answers 201. The session is available.",
    ],
    "vague": [
        "Step four: a vague request, with no duration. "
        "The planner chooses QoS provisioning instead of a timed session.",
    ],
    "faults": [
        "Step five: we inject faults into correct plans.",
    ],
    "faults_res": [
        "Schema and telecom-rule errors are caught and repaired. "
        "Calls to unpublished APIs are blocked by the registry layer.",
    ],
    "load": [
        "Step six: a short load test. Every request goes through the live registry check.",
    ],
    "load_res": [
        "All requests succeed. This short run shares the CPU with the screen recorder.",
    ],
    "results": [
        "On three hundred test intents, GPT, Gemini and Claude all exceed ninety-five percent success, "
        "and the platform serves about one hundred and sixty requests per second.",
    ],
    "end": [
        "Thank you. The code and data are on GitHub.",
    ],
}


def clip(key: str, i: int) -> Path:
    return OUT / f"{key}_{i}.mp3"


async def _generate():
    import edge_tts
    from mutagen.mp3 import MP3

    OUT.mkdir(parents=True, exist_ok=True)
    durations = {}
    for key, lines in NARRATION.items():
        for i, text in enumerate(lines):
            p = clip(key, i)
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(p))
            durations[p.name] = round(MP3(p).info.length, 3)
    (OUT / "durations.json").write_text(json.dumps(durations, indent=1))
    print(f"{len(durations)} clips, {sum(durations.values()):.0f} s of speech")


def durations() -> dict:
    return json.loads((OUT / "durations.json").read_text())


if __name__ == "__main__":
    asyncio.run(_generate())
