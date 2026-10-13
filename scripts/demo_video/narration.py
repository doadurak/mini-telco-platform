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
        "This is a live demo of our CAPIF-compliant, multi-LLM intent orchestration platform.",
        "It turns a natural-language request into a validated network API call on a real 5G core.",
    ],
    "arch": [
        "An operator writes an intent in plain English or Turkish.",
        "A two-phase LLM planner first selects a CAMARA service, then generates its payload.",
        "Every plan passes three validation layers: schema, telecom rules, and a live check "
        "against the OpenCAPIF registry.",
        "Valid plans are executed through CAMARA and the NEF, on an Open5GS core with UERANSIM devices.",
    ],
    "status": [
        "Step one: the testbed. Everything you see is running in containers.",
        "OpenCAPIF, the CAMARA and NEF providers, the Open5GS core, and three simulated phones, "
        "each with its own IP address.",
    ],
    "discover": [
        "Step two: service discovery.",
        "The platform is onboarded to OpenCAPIF as an invoker, and discovers the published network APIs "
        "over mutual TLS.",
    ],
    "dry": [
        "Step three: a dry run. We ask for video-streaming quality for one phone, for thirty minutes.",
        "The LLM selects Quality on Demand and builds the CAMARA payload.",
        "All three validation layers pass, and the registry check is live. Nothing is sent to the network yet.",
    ],
    "live": [
        "Step four: the same request, now live.",
        "The provider resolves the phone's IP address from the 5G core subscriber database, "
        "and maps streaming to an operator QoS profile.",
        "On the right, the NEF forwards the request to the Open5GS policy control function, "
        "which answers with 201. The session is available.",
    ],
    "vague": [
        "Step five: a vague request. The user asks for better quality for a long time, with no duration.",
        "The planner chooses QoS provisioning instead of a time-limited session.",
        "The plan is validated, and the assignment becomes active on the core.",
    ],
    "switch": [
        "Step six: the LLM backend can be switched at run time. Here we switch to Claude Haiku.",
        "The same request gives the same validated CAMARA plan.",
    ],
    "faults": [
        "Step seven: fault injection. We break correct plans on purpose, one fault type at a time.",
    ],
    "faults_res": [
        "Schema and telecom-rule errors are caught, and repaired by the LLM feedback loop.",
        "A call to an unpublished API is always caught by the registry layer. It cannot be repaired, "
        "so it is never executed.",
    ],
    "load": [
        "Step eight: a short load test. Every request goes through the live registry check.",
    ],
    "load_res": [
        "This run shares the CPU with the screen recorder. "
        "The full run in the paper reaches about one hundred and sixty requests per second.",
    ],
    "results": [
        "On three hundred test intents, the best model completes ninety-seven point three percent "
        "of the intents correctly.",
        "Without the two-phase design, this drops to seventy-seven percent, "
        "and without registry grounding, to sixteen percent.",
    ],
    "end": [
        "Thank you for watching. The code, datasets and scripts are available on GitHub.",
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
