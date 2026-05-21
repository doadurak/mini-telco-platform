#!/usr/bin/env python3
"""
run_stability_test.py — Stability Score (SS) measurement.

Runs the same set of intents N times and computes the SS metric:
  SS = 1 - (distinct_outputs - 1) / runs

An output is considered "distinct" when either the selected service_id
differs from the majority or the IWSR result (pass/fail) flips.

Usage:
  # Run 5 repetitions on a 10-entry sample (LLM mode)
  python scripts/run_stability_test.py \
    --mode llm-assisted \
    --runs 5 \
    --max 10 \
    --delay 3 \
    --output datasets/stability_results.json

  # Deterministic (no API — instant)
  python scripts/run_stability_test.py \
    --mode deterministic \
    --runs 10 \
    --output datasets/stability_det.json
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

# Ensure backend package is importable when run from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.evaluation_engine import evaluate_entry, load_dataset


# ─── Stability computation ────────────────────────────────────────────────────

def compute_ss_for_entry(entry_id: str, outcomes: list[dict]) -> float:
    """
    SS for a single entry across N runs.
    Outcome key = (service_id, iwsr).
    SS = 1 - (distinct - 1) / N
    """
    keys = [(o.get("actual_service_id"), o.get("iwsr")) for o in outcomes]
    distinct = len(set(keys))
    n = len(keys)
    if n <= 1:
        return 1.0
    return max(0.0, 1.0 - (distinct - 1) / n)


def compute_global_ss(per_entry_ss: list[float]) -> float:
    return sum(per_entry_ss) / len(per_entry_ss) if per_entry_ss else 0.0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure Stability Score (SS) by running N repeated evaluations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--mode", choices=["deterministic", "llm-assisted"], default="llm-assisted")
    parser.add_argument("--runs", type=int, default=5, help="Number of repetitions (default: 5)")
    parser.add_argument("--max", dest="max_entries", type=int, default=None,
                        help="Limit entries to N (default: all 60)")
    parser.add_argument("--delay", dest="delay_s", type=float, default=3.0,
                        help="Delay between LLM requests in seconds (default: 3.0)")
    parser.add_argument("--category", default=None, help="Filter by category")
    parser.add_argument("--difficulty", default=None, help="Filter by difficulty")
    parser.add_argument("--output", type=Path, default=None, help="Save results to JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    entries = load_dataset()
    if args.category:
        entries = [e for e in entries if e.get("category") == args.category]
    if args.difficulty:
        entries = [e for e in entries if e.get("difficulty") == args.difficulty]
    if args.max_entries:
        entries = entries[:args.max_entries]

    print(f"Stability test: mode={args.mode}, runs={args.runs}, entries={len(entries)}")
    print(f"Total API calls: {len(entries) * args.runs * (2 if args.mode == 'llm-assisted' else 0)}")
    print()

    # run_results[entry_id] = list of per-run outcome dicts
    run_results: dict[str, list[dict]] = {e["id"]: [] for e in entries}

    for run_idx in range(1, args.runs + 1):
        print(f"── Run {run_idx}/{args.runs} ──────────────────────────────")
        for i, entry in enumerate(entries):
            result = evaluate_entry(entry, mode=args.mode, dry_run=True, use_feedback=False)
            outcome = {
                "run": run_idx,
                "iwsr": result.iwsr,
                "actual_service_id": result.actual_service_id,
                "error": result.error,
                "latency_ms": round(result.latency_ms, 1),
            }
            run_results[entry["id"]].append(outcome)

            if args.verbose:
                status = "OK" if result.iwsr else f"FAIL: svc={result.actual_service_id}"
                print(f"  [{entry['id']:20s}] {status}")

            # Delay between requests (LLM mode)
            is_last = (run_idx == args.runs and i == len(entries) - 1)
            if args.mode == "llm-assisted" and args.delay_s > 0 and not is_last:
                time.sleep(args.delay_s)

        print()

    # ── Compute per-entry SS ──────────────────────────────────────────────────
    entry_ss: dict[str, float] = {}
    for eid, outcomes in run_results.items():
        entry_ss[eid] = compute_ss_for_entry(eid, outcomes)

    global_ss = compute_global_ss(list(entry_ss.values()))

    # ── Print report ──────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"  STABILITY REPORT  (mode={args.mode}, runs={args.runs})")
    print("=" * 60)
    print(f"  Global SS:  {global_ss:.4f}  ({global_ss*100:.1f}%)")
    print()

    unstable = [(eid, ss) for eid, ss in entry_ss.items() if ss < 1.0]
    if unstable:
        print(f"  Unstable entries ({len(unstable)}):")
        for eid, ss in sorted(unstable, key=lambda x: x[1]):
            outcomes = run_results[eid]
            svc_counter = Counter(o.get("actual_service_id") for o in outcomes)
            print(f"    {eid:25s}  SS={ss:.3f}  services={dict(svc_counter)}")
    else:
        print("  All entries perfectly stable (SS = 1.0)")

    # Per-difficulty SS
    diff_ss: dict[str, list[float]] = {}
    for entry in entries:
        d = entry.get("difficulty", "?")
        diff_ss.setdefault(d, []).append(entry_ss[entry["id"]])
    print()
    print("  SS by difficulty:")
    for diff in ["easy", "medium", "hard"]:
        vals = diff_ss.get(diff, [])
        avg = sum(vals) / len(vals) if vals else 0.0
        print(f"    {diff:<8}  {avg:.4f}  ({avg*100:.1f}%)")

    # ── Save ──────────────────────────────────────────────────────────────────
    if args.output:
        out = {
            "mode": args.mode,
            "runs": args.runs,
            "entries": len(entries),
            "global_ss": round(global_ss, 4),
            "per_entry_ss": {k: round(v, 4) for k, v in entry_ss.items()},
            "run_results": run_results,
        }
        args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResults saved to {args.output}")

    print()


if __name__ == "__main__":
    main()
