#!/usr/bin/env python3
"""
Table I of the WMNC camera-ready: three runs per LLM planner on the 300 intents, per-difficulty
IWSR, the function-calling baseline, and the service cross-check against the keyword planner.

  python scripts/summarize_runs.py        # prints the table, writes datasets/repeats/summary.json
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "datasets"
RUNS = {
    "Keyword baseline": [D / "eval_results_deterministic_300.json"],
    "GPT-4o-mini": [D / f"repeats/eval_results_gpt4omini_300_run{r}.json" for r in (1, 2, 3)],
    "Claude Haiku 4.5": [D / "eval_results_llm_anthropic_haiku45_300.json"]
                        + [D / f"repeats/eval_results_haiku45_300_run{r}.json" for r in (2, 3)],
    "Gemini 2.5 Flash": [D / "eval_results_gemini25flash_300.json"]
                        + [D / f"repeats/eval_results_gemini25flash_300_run{r}.json" for r in (2, 3)],
    "GPT-4o-mini function calling": [D / "eval_results_gpt4omini_function_calling_300.json"],
    "GPT-4o-mini function calling + L1-L3 feedback": [D / "eval_results_gpt4omini_function_calling_feedback_300.json"],
}
LEVELS = ("easy", "medium", "hard")


def _results(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]
    assert len(rows) == 300 and not any(r.get("error") for r in rows), path
    return rows


def main() -> None:
    gt = {e["id"]: e["expected"]["service_id"]
          for e in json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))["entries"]}
    keyword = {r["id"]: r["actual_service_id"] for r in _results(RUNS["Keyword baseline"][0])}
    summary = {}
    for name, paths in RUNS.items():
        runs = [_results(p) for p in paths]
        pct = lambda f: [100 * sum(map(f, rows)) / len(rows) for rows in runs]  # noqa: E731
        row = {"runs": len(runs),
               "IWSR": pct(lambda r: r["iwsr"]),
               "SCR": pct(lambda r: r["l1_passed"]),
               "wrong_service": pct(lambda r: not r["service_correct"]),
               "repaired": [sum(r.get("feedback_recovered", False) for r in rows) for rows in runs]}
        for lvl in LEVELS:
            row[lvl] = [100 * st.mean(r["iwsr"] for r in rows if r["difficulty"] == lvl) for rows in runs]
        if name != "Keyword baseline":
            # cross-check: plans whose service differs from the keyword planner's are held
            wrong = [sum(1 for r in rows if not r["service_correct"]) for rows in runs]
            caught = [sum(1 for r in rows if not r["service_correct"] and keyword[r["id"]] != r["actual_service_id"])
                      for rows in runs]
            held = [100 * sum(1 for r in rows if r["service_correct"] and keyword[r["id"]] != r["actual_service_id"])
                    / sum(1 for r in rows if r["service_correct"]) for rows in runs]
            row["crosscheck"] = {"wrong": wrong, "caught": caught, "correct_held_pct": held}
        summary[name] = row
        span = lambda v: f"{st.mean(v):5.1f}" + (f" [{min(v):.1f}-{max(v):.1f}]" if len(v) > 1 else "")  # noqa: E731
        print(f"{name:46s} IWSR {span(row['IWSR'])}  " + "  ".join(f"{l} {span(row[l])}" for l in LEVELS)
              + f"  wrong svc {span(row['wrong_service'])}  repaired {row['repaired']}")
        if "crosscheck" in row:
            c = row["crosscheck"]
            print(f"{'':46s} cross-check caught {c['caught']} of {c['wrong']} wrong services; "
                  f"held {span(c['correct_held_pct'])}% of correct plans")
    (D / "repeats" / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
