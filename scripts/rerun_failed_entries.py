#!/usr/bin/env python3
"""
Re-run, in place, the entries of a recorded evaluation that ended in an error.

Only entries with a non-null "error" are re-evaluated (LLM-assisted, live L3); all
other records are kept byte-for-byte, then the summary is recomputed from every
record. Before touching anything, the summary recomputed from the unchanged file
must equal the stored one, so the rewrite cannot silently shift other metrics.
Each re-run record gets a "rerun" note; the previous error is kept in "previous_error".

Usage (inside the backend container, where the LLM keys and CAPIF credentials live):
  python scripts/rerun_failed_entries.py datasets/eval_results_gpt4omini_300.json \
      --provider openai --note "2026-10-11: Phase-1 multi-intent list support"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.evaluation_engine import DATASET_PATH, EntryResult, EvaluationReport, evaluate_entry  # noqa: E402
from backend.llm_planner import set_llm_provider  # noqa: E402

_RESULT_FIELDS = [
    "service_correct", "l1_passed", "l2_passed", "l3_passed", "registry_checked", "iwsr",
    "feedback_attempted", "feedback_recovered", "actual_service_id", "actual_payload", "error",
]


def _entry_result(r: dict, mode: str) -> EntryResult:
    return EntryResult(
        entry_id=r["id"], intent=r.get("intent", ""), language=r.get("language", "en"),
        difficulty=r.get("difficulty", "medium"), category=r.get("category", "unknown"),
        mode=r.get("mode", mode), expected_service_id="", expected_operation_id="",
        actual_service_id=r.get("actual_service_id"), actual_payload=r.get("actual_payload"),
        service_correct=r.get("service_correct", False), l1_passed=r.get("l1_passed", False),
        l2_passed=r.get("l2_passed", False), l3_passed=r.get("l3_passed", False),
        registry_checked=r.get("registry_checked", False), iwsr=r.get("iwsr", False),
        feedback_attempted=r.get("feedback_attempted", False),
        feedback_recovered=r.get("feedback_recovered", False), error=r.get("error"),
    )


def _summary(results: list[dict], mode: str) -> dict:
    report = EvaluationReport(mode=mode)
    for r in results:
        report.add(_entry_result(r, mode))
    return report.summary()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--provider", required=True, choices=["openai", "anthropic", "gemini"])
    ap.add_argument("--note", required=True)
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait before each entry (rate limits)")
    args = ap.parse_args()

    data = json.loads(args.file.read_text(encoding="utf-8"))
    mode = data["summary"]["mode"]
    if _summary(data["results"], mode) != data["summary"]:
        sys.exit(f"{args.file}: stored summary does not match its records; refusing to rewrite")

    entries = {e["id"]: e for e in json.loads(DATASET_PATH.read_text(encoding="utf-8"))["entries"]}
    set_llm_provider(args.provider)

    for r in data["results"]:
        if not r.get("error"):
            continue
        if args.delay:
            time.sleep(args.delay)
        new = evaluate_entry(entries[r["id"]], mode=mode, check_registry=True)
        previous = r.get("previous_error") or r["error"]  # keep the original error across retries
        for key in _RESULT_FIELDS:
            r[key] = getattr(new, key)
        r["latency_ms"] = round(new.latency_ms, 1)
        r["previous_error"] = previous
        r["rerun"] = args.note
        print(f"{r['id']:12s} -> {new.actual_service_id} iwsr={new.iwsr} "
              f"registry_checked={new.registry_checked} error={new.error}")

    before = data["summary"]
    data["summary"] = _summary(data["results"], mode)
    args.file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for k in ("IWSR", "SCR", "SVR", "HR", "SS", "RRF"):
        print(f"  {k}: {before['metrics'][k]} -> {data['summary']['metrics'][k]}")


if __name__ == "__main__":
    main()
