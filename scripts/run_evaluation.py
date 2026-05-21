"""
Reliability Evaluation CLI

Usage:
  venv/bin/python scripts/run_evaluation.py [options]

Examples:
  # Deterministic mode, full dataset
  venv/bin/python scripts/run_evaluation.py

  # LLM-assisted mode, English only, first 10 entries
  venv/bin/python scripts/run_evaluation.py --mode llm-assisted --lang en --max 10

  # Compare both modes on QoD entries only
  venv/bin/python scripts/run_evaluation.py --compare --category qod_session

  # Quick smoke test (5 entries, deterministic)
  venv/bin/python scripts/run_evaluation.py --max 5 --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path so we can import backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.evaluation_engine import (
    EvaluationReport,
    compare_modes,
    run_evaluation,
)


def _print_report(report: EvaluationReport, verbose: bool = False) -> None:
    summary = report.summary()
    print(f"\n{'='*60}")
    print(f"  Mode: {summary['mode'].upper()}")
    print(f"  Entries evaluated: {summary['total_entries']}")
    print(f"{'='*60}")

    metrics = summary["metrics"]
    print(f"  IWSR  (Intent-to-Workflow Success Rate): {metrics['IWSR']:.1%}")
    print(f"  SCR   (Schema Compliance Rate):          {metrics['SCR']:.1%}")
    print(f"  SVR   (Semantic Validity Rate):          {metrics['SVR']:.1%}")
    print(f"  HR    (Hallucination Rate):              {metrics['HR']:.1%}")
    print(f"  SS    (Stability Score):                 {metrics['SS']:.4f}")
    print(f"  RRF   (Recovery Rate after Feedback):    {metrics['RRF']:.1%}")

    print(f"\n  Stratified IWSR by difficulty:")
    for diff, rate in summary.get("stratified_iwsr", {}).items():
        bar = "█" * int(rate * 20)
        print(f"    {diff:<10} {rate:.1%}  {bar}")

    raw = summary["raw_counts"]
    if raw.get("feedback_attempted", 0) > 0:
        print(f"\n  Feedback loop: {raw['feedback_recovered']}/{raw['feedback_attempted']} recovered")

    if verbose:
        print(f"\n  {'ID':<20} {'SVC OK':>6} {'L1':>4} {'L2':>4} {'IWSR':>6} {'ERR':<40}")
        print(f"  {'-'*20} {'------':>6} {'----':>4} {'----':>4} {'------':>6} {'-'*40}")
        for r in report.results:
            svc_ok = "OK" if r.service_correct else "FAIL"
            l1 = "OK" if r.l1_passed else "FAIL"
            l2 = "OK" if r.l2_passed else "FAIL"
            iwsr = "OK" if r.iwsr else "FAIL"
            err = (r.error or "")[:38]
            print(f"  {r.entry_id:<20} {svc_ok:>6} {l1:>4} {l2:>4} {iwsr:>6} {err:<40}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reliability Evaluation Engine — CAMARA/CAPIF Intent-to-API"
    )
    parser.add_argument(
        "--mode",
        choices=["deterministic", "llm-assisted", "llm-single"],
        default="deterministic",
        help="Orchestration mode: deterministic | llm-assisted (2 API calls/entry) | llm-single (1 API call/entry, quota-efficient)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run both modes and show side-by-side comparison",
    )
    parser.add_argument(
        "--category",
        choices=["qod_session", "qos_profiles", "qos_provisioning", "location_retrieval", "edge_case"],
        default=None,
        help="Filter by service category",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "tr"],
        default=None,
        help="Filter by language (en=English, tr=Turkish)",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default=None,
        help="Filter by difficulty level",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_entries",
        help="Limit number of entries (useful for quick tests)",
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Disable feedback correction loop for LLM-assisted mode",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-entry results table",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON (for programmatic use)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Save JSON results to file",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        dest="request_delay_s",
        help="Seconds between LLM API calls to avoid rate limits (default: 4.0)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Print per-entry progress while running",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        dest="resume_from",
        help="Resume from a previous partial JSON output file (skips already-completed entries)",
    )

    args = parser.parse_args()
    use_feedback = not args.no_feedback

    if args.compare:
        print("Running comparison: deterministic vs llm-assisted ...")
        result = compare_modes(
            dry_run=True,
            use_feedback=use_feedback,
            max_entries=args.max_entries,
        )
        if args.json_output or args.output:
            out = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                args.output.write_text(out, encoding="utf-8")
                print(f"Saved to {args.output}")
            else:
                print(out)
        else:
            print("\n=== DETERMINISTIC ===")
            if isinstance(result.get("deterministic"), dict):
                m = result["deterministic"]["metrics"]
                for k, v in m.items():
                    print(f"  {k}: {v:.1%}" if k != "SS" else f"  {k}: {v:.4f}")

            print("\n=== LLM-ASSISTED ===")
            if isinstance(result.get("llm-assisted"), dict):
                m = result["llm-assisted"]["metrics"]
                for k, v in m.items():
                    print(f"  {k}: {v:.1%}" if k != "SS" else f"  {k}: {v:.4f}")
            else:
                print(f"  {result.get('llm-assisted')}")

            if "delta" in result:
                print("\n=== DELTA (LLM - Deterministic) ===")
                for k, v in result["delta"].items():
                    sign = "+" if v >= 0 else ""
                    print(f"  {k}: {sign}{v:.4f}")
        return

    print(f"Running evaluation: mode={args.mode}, lang={args.lang or 'all'}, "
          f"category={args.category or 'all'}, difficulty={args.difficulty or 'all'}, "
          f"max={args.max_entries or 'all'}")

    delay = args.request_delay_s if args.mode in ("llm-assisted", "llm-single") else 0.0
    report = run_evaluation(
        mode=args.mode,
        dry_run=True,
        use_feedback=use_feedback,
        filter_category=args.category,
        filter_language=args.lang,
        filter_difficulty=args.difficulty,
        max_entries=args.max_entries,
        request_delay_s=delay,
        verbose=args.progress,
        resume_from=args.resume_from,
    )

    if args.json_output or args.output:
        out_data = {
            "summary": report.summary(),
            "results": [
                {
                    "id": r.entry_id,
                    "intent": r.intent,
                    "language": r.language,
                    "difficulty": r.difficulty,
                    "category": r.category,
                    "mode": r.mode,
                    "service_correct": r.service_correct,
                    "l1_passed": r.l1_passed,
                    "l2_passed": r.l2_passed,
                    "iwsr": r.iwsr,
                    "feedback_attempted": r.feedback_attempted,
                    "feedback_recovered": r.feedback_recovered,
                    "actual_service_id": r.actual_service_id,
                    "actual_payload": r.actual_payload,
                    "error": r.error,
                    "latency_ms": round(r.latency_ms, 1),
                }
                for r in report.results
            ],
        }
        out = json.dumps(out_data, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(out, encoding="utf-8")
            print(f"Results saved to {args.output}")
        else:
            print(out)
    else:
        _print_report(report, verbose=args.verbose)


if __name__ == "__main__":
    main()
