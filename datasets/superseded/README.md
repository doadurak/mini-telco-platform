# Superseded results

`eval_results_gpt4omini_300_mixed.json` was reported as GPT-4o-mini in the WMNC submission (IWSR 97.3%).
Only 65 entries were planned by GPT-4o-mini (the 60 pilot entries and 5 multi-intent entries re-run on
2026-10-11); the other 235 were run with `LLM_PROVIDER=gpt`, which the planner did not recognise and
silently replaced with Gemini 2.5 Flash. Each result now carries `provider` and `model`
(`scripts/backfill_provenance.py`).
The planner now rejects unknown provider names.

The GPT-4o-mini results are now `datasets/repeats/eval_results_gpt4omini_300_run{1,2,3}.json`
(IWSR 96.7 / 96.7 / 96.3%). The file is kept because `scripts/layer_fault_injection.py` samples the
correct plans for `datasets/layer_faults.json` from it; the faults are injected into those plans and
repaired by GPT-4o-mini.
