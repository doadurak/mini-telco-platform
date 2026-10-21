#!/usr/bin/env python3
"""
One-off (2026-10-21): add provider/model to result files written before run_evaluation.py recorded
them. Each assignment below was verified, not assumed:

- runs of 2026-10-21 were started in this repository with an explicit LLM_PROVIDER;
- the Claude/Gemini 300-entry files cluster with their own repeat runs (277-284/300 identical
  payloads) and not with the other models (<200);
- the two GPT-4o-mini ablations were reproduced on 30 entries: GPT-4o-mini gives 30/30 and 21/30
  identical payloads, Claude Haiku 4.5 17/30 and 0/30;
- in the superseded GPT file only the 60 pilot entries and the entries re-run by
  rerun_failed_entries.py (provider openai) are GPT-4o-mini; the rest are Gemini 2.5 Flash.

  python scripts/backfill_provenance.py
"""
from __future__ import annotations

import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "datasets"
GPT, HAIKU, GEMINI = ("openai", "gpt-4o-mini"), ("anthropic", "claude-haiku-4-5-20251001"), ("gemini", "gemini-2.5-flash")
FILES = {
    "eval_results_deterministic_300.json": ("keyword", "keyword-planner"),
    "eval_results_llm_anthropic_haiku45_300.json": HAIKU,
    "eval_results_gemini25flash_300.json": GEMINI,
    "eval_results_gpt4omini_single_300.json": GPT,
    "eval_results_gpt4omini_ungrounded_300.json": GPT,
    "eval_results_gpt4omini_function_calling_300.json": GPT,
    "eval_results_gpt4omini_function_calling_feedback_300.json": GPT,
    **{f"repeats/eval_results_gpt4omini_300_run{r}.json": GPT for r in (1, 2, 3)},
    **{f"repeats/eval_results_haiku45_300_run{r}.json": HAIKU for r in (2, 3)},
    **{f"repeats/eval_results_gemini25flash_300_run{r}.json": GEMINI for r in (2, 3)},
}
NOTE = "provider/model backfilled 2026-10-21 by scripts/backfill_provenance.py"


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    for name, (provider, model) in FILES.items():
        path = D / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["summary"].update(provider=provider, model=model, provenance=NOTE)
        for r in data["results"]:
            r.setdefault("provider", provider)
            r.setdefault("model", model)
        _write(path, data)
        print(f"{name}: {model}")

    path = D / "superseded" / "eval_results_gpt4omini_300_mixed.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    pilot = {r["id"] for r in json.loads((D / "legacy_pilot_60" / "eval_results_gpt4omini.json")
                                         .read_text(encoding="utf-8"))["results"]}
    counts = {}
    for r in data["results"]:
        provider, model = GPT if (r["id"] in pilot or r.get("rerun")) else GEMINI
        r["provider"], r["model"] = provider, model
        counts[model] = counts.get(model, 0) + 1
    data["summary"].update(provider="mixed", model="mixed", model_counts=counts, provenance=NOTE)
    _write(path, data)
    print(f"superseded mixed file: {counts}")


if __name__ == "__main__":
    main()
