#!/usr/bin/env python3
"""
Concurrency load test for POST /orchestrate.

  deterministic : keyword planner + L1-L3 (live CAPIF registry), no LLM -> platform capacity
  llm-assisted  : two-phase LLM planner + L1-L3 -> shows where the bottleneck is

Requests use dry_run=true (no provider side effects, e.g. QoD sessions) but keep the
live registry check. Intents are drawn from the ground-truth dataset.

  python scripts/load_test.py --output datasets/load_test.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

API = "http://localhost:8000/orchestrate"


def _one(intent: str, mode: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = requests.post(API, json={"intent": intent, "dry_run": True, "check_registry": True,
                                     "orchestration_mode": mode}, timeout=120)
        ok = r.status_code == 200
        body = r.json() if ok else {}
    except requests.RequestException:
        ok, body = False, {}
    return {"ok": ok, "client_ms": (time.perf_counter() - t0) * 1000,
            "timings": body.get("timings_ms", {}),
            "registry_checked": body.get("validation", {}).get("registry_checked", False)}


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] if xs else 0.0


def run_level(intents, mode, concurrency, n):
    work = [intents[i % len(intents)] for i in range(n)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        res = list(pool.map(lambda it: _one(it, mode), work))
    wall = time.perf_counter() - t0
    ok = [r for r in res if r["ok"]]
    lat = [r["client_ms"] for r in ok]
    plan = [r["timings"].get("planning", 0) for r in ok]
    val = [r["timings"].get("validation", 0) for r in ok]
    return {
        "mode": mode, "concurrency": concurrency, "requests": n, "ok": len(ok),
        "registry_checked": sum(r["registry_checked"] for r in ok),
        "throughput_rps": round(len(ok) / wall, 2),
        "p50_ms": round(_pct(lat, 50)), "p95_ms": round(_pct(lat, 95)),
        "median_planning_ms": round(statistics.median(plan), 1) if plan else None,
        "median_validation_ms": round(statistics.median(val), 1) if val else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--det-levels", default="1,5,10,20")
    ap.add_argument("--det-requests", type=int, default=60)
    ap.add_argument("--llm-levels", default="1,5,10")
    ap.add_argument("--llm-requests", type=int, default=20)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    entries = json.loads(Path("datasets/ground_truth.json").read_text(encoding="utf-8"))["entries"]
    intents = [e["intent"] for e in entries if e["category"] != "edge_case"]

    rows = []
    for c in map(int, args.det_levels.split(",")):
        rows.append(run_level(intents, "deterministic", c, args.det_requests)); print(rows[-1])
    for c in map(int, args.llm_levels.split(",")):
        rows.append(run_level(intents, "llm-assisted", c, args.llm_requests)); print(rows[-1])
    if args.output:
        args.output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
