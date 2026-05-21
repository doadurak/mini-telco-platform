#!/usr/bin/env python3
"""
analyze_results.py — Evaluation result analysis and comparison.

Reads one or two evaluation JSON result files and produces:
  - Per-metric summary table
  - Language (EN/TR) breakdown
  - Difficulty (easy/medium/hard) breakdown
  - Category breakdown
  - Side-by-side comparison (if two files given)
  - Failed entry details

Usage:
  # Single file analysis
  python scripts/analyze_results.py datasets/eval_results_deterministic.json

  # Comparison: deterministic vs LLM
  python scripts/analyze_results.py \
    datasets/eval_results_deterministic.json \
    datasets/eval_results_llm_anthropic.json

  # Export to CSV
  python scripts/analyze_results.py \
    datasets/eval_results_deterministic.json \
    datasets/eval_results_llm_anthropic.json \
    --csv datasets/comparison.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("results", [])


def pct(num: int, den: int) -> str:
    if den == 0:
        return "N/A"
    return f"{num/den*100:.1f}%"


def bar(val: float, width: int = 20) -> str:
    filled = round(val * width)
    return "█" * filled + "░" * (width - filled)


# ─── Metric computation ───────────────────────────────────────────────────────

def compute_metrics(results: list[dict]) -> dict[str, Any]:
    ok = [r for r in results if not r.get("error")]
    errors = [r for r in results if r.get("error")]

    if not ok:
        return {
            "total": len(results), "processed": 0, "errors": len(errors),
            "IWSR": 0.0, "SCR": 0.0, "SVR": 0.0, "HR": 1.0, "SS": 0.0,
            "iwsr_n": 0, "scr_n": 0, "svr_n": 0, "hr_n": 0,
        }

    iwsr_n = sum(1 for r in ok if r.get("iwsr"))
    scr_n  = sum(1 for r in ok if r.get("l1_passed"))
    svr_n  = sum(1 for r in ok if r.get("l2_passed"))
    hr_n   = sum(1 for r in ok if not r.get("service_correct"))

    # Stability Score: average consistency per difficulty group
    by_diff: dict[str, list[bool]] = {}
    for r in ok:
        d = r.get("difficulty", "unknown")
        by_diff.setdefault(d, []).append(bool(r.get("iwsr")))

    ss_scores = []
    for vals in by_diff.values():
        if len(vals) > 1:
            p = sum(vals) / len(vals)
            ss_scores.append(1 - abs(p - round(p)))
        elif vals:
            ss_scores.append(1.0 if vals[0] else 0.0)
    ss = sum(ss_scores) / len(ss_scores) if ss_scores else 0.0

    return {
        "total": len(results),
        "processed": len(ok),
        "errors": len(errors),
        "IWSR": iwsr_n / len(ok),
        "SCR":  scr_n  / len(ok),
        "SVR":  svr_n  / len(ok),
        "HR":   hr_n   / len(ok),
        "SS":   ss,
        "iwsr_n": iwsr_n, "scr_n": scr_n, "svr_n": svr_n, "hr_n": hr_n,
        "n": len(ok),
    }


def breakdown_by(results: list[dict], key: str) -> dict[str, dict]:
    groups: dict[str, list] = {}
    for r in results:
        if not r.get("error"):
            groups.setdefault(r.get(key, "?"), []).append(r)
    return {k: compute_metrics(v) for k, v in sorted(groups.items())}


# ─── Display ──────────────────────────────────────────────────────────────────

def print_summary(label: str, m: dict, results: list[dict]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  {m['processed']}/{m['total']} entries processed  ({m['errors']} errors)")
    print(f"{'=' * 60}")
    print(f"  {'Metric':<8}  {'Value':>8}  {'Bar':<22}  Count")
    print(f"  {'-'*55}")

    for metric, val, n_key, den_key in [
        ("IWSR",  m["IWSR"], "iwsr_n", "n"),
        ("SCR",   m["SCR"],  "scr_n",  "n"),
        ("SVR",   m["SVR"],  "svr_n",  "n"),
        ("HR",    m["HR"],   "hr_n",   "n"),
        ("SS",    m["SS"],   None,     None),
    ]:
        count_str = f"{m[n_key]}/{m[den_key]}" if n_key else f"{val:.4f}"
        print(f"  {metric:<8}  {val*100:>7.1f}%  {bar(val):<22}  {count_str}")

    # Language breakdown
    by_lang = breakdown_by(results, "language")
    if by_lang:
        print(f"\n  Language breakdown (IWSR):")
        for lang, lm in by_lang.items():
            print(f"    {lang.upper():<6} {lm['IWSR']*100:>6.1f}%  {bar(lm['IWSR'], 16)}  {lm['iwsr_n']}/{lm['n']}")

    # Difficulty breakdown
    by_diff = breakdown_by(results, "difficulty")
    if by_diff:
        print(f"\n  Difficulty breakdown (IWSR):")
        for diff, dm in by_diff.items():
            print(f"    {diff:<8} {dm['IWSR']*100:>6.1f}%  {bar(dm['IWSR'], 16)}  {dm['iwsr_n']}/{dm['n']}")

    # Category breakdown
    by_cat = breakdown_by(results, "category")
    if by_cat:
        print(f"\n  Category breakdown (IWSR):")
        for cat, cm in by_cat.items():
            print(f"    {cat:<30} {cm['IWSR']*100:>6.1f}%  {cm['iwsr_n']}/{cm['n']}")

    # Failed entries
    failed = [r for r in results if not r.get("error") and not r.get("iwsr")]
    if failed:
        print(f"\n  Failed entries ({len(failed)}):")
        for r in failed:
            exp = r.get("expected_service_id", "?")
            got = r.get("actual_service_id", "?")
            err = r.get("error", "")
            intent_short = r.get("intent", "")[:55]
            print(f"    [{r['id']:20s}] expected={exp} got={got}")
            print(f"      intent: {intent_short}")
            if err:
                print(f"      error:  {err[:70]}")


def print_comparison(label_a: str, m_a: dict, label_b: str, m_b: dict) -> None:
    print(f"\n{'=' * 72}")
    print(f"  COMPARISON: {label_a}  vs  {label_b}")
    print(f"{'=' * 72}")
    print(f"  {'Metric':<8}  {label_a:>20}  {label_b:>20}  {'Delta':>10}")
    print(f"  {'-'*68}")
    for metric in ["IWSR", "SCR", "SVR", "HR", "SS"]:
        va = m_a.get(metric, 0)
        vb = m_b.get(metric, 0)
        delta = vb - va
        sign = "+" if delta >= 0 else ""
        print(f"  {metric:<8}  {va*100:>19.1f}%  {vb*100:>19.1f}%  {sign}{delta*100:>8.1f}%")


# ─── CSV export ───────────────────────────────────────────────────────────────

def export_csv(path: Path, label_a: str, m_a: dict, label_b: str | None, m_b: dict | None) -> None:
    rows = []
    metrics = ["IWSR", "SCR", "SVR", "HR", "SS"]
    if m_b:
        rows.append(["Metric", label_a, label_b, "Delta"])
        for m in metrics:
            va = m_a.get(m, 0)
            vb = m_b.get(m, 0)
            rows.append([m, f"{va:.4f}", f"{vb:.4f}", f"{vb - va:+.4f}"])
    else:
        rows.append(["Metric", label_a])
        for m in metrics:
            rows.append([m, f"{m_a.get(m, 0):.4f}"])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"\nCSV saved to {path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze and compare evaluation result JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file_a", type=Path, help="First result file (e.g. deterministic)")
    parser.add_argument("file_b", type=Path, nargs="?", help="Second result file (e.g. LLM)")
    parser.add_argument("--csv", type=Path, metavar="PATH", help="Export comparison to CSV")
    args = parser.parse_args()

    if not args.file_a.exists():
        print(f"Error: file not found: {args.file_a}", file=sys.stderr)
        sys.exit(1)

    results_a = load(args.file_a)
    m_a = compute_metrics(results_a)
    label_a = args.file_a.stem

    print_summary(label_a, m_a, results_a)

    m_b = None
    if args.file_b:
        if not args.file_b.exists():
            print(f"Error: file not found: {args.file_b}", file=sys.stderr)
            sys.exit(1)
        results_b = load(args.file_b)
        m_b = compute_metrics(results_b)
        label_b = args.file_b.stem
        print_summary(label_b, m_b, results_b)
        print_comparison(label_a, m_a, label_b, m_b)

    if args.csv:
        export_csv(args.csv, label_a, m_a, label_b if args.file_b else None, m_b)

    print()


if __name__ == "__main__":
    main()
